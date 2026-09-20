from __future__ import annotations

from unittest.mock import MagicMock

import httpx2
import pytest
from typesafe_sdk import ChoiceAnswer, TypeSafeAuthenticationError

from issue_triage.classifier import ClassifierError, FakeClassifier, parse_jev_min_confidence
from issue_triage.classifier_factory import get_classifier, get_classifier_for_eval
from issue_triage.jev_classifier import JevClassifier
from issue_triage.models import ClassificationProposal, IssueInput
from issue_triage.pipeline import TriagePipeline
from sqlalchemy import create_engine

from issue_triage.db import init_db, make_session_factory
from issue_triage.repository import IssueRepository


def _choice(name: str, confidence: float) -> ChoiceAnswer:
    return ChoiceAnswer(
        type="choice",
        choice=name,
        confidence=confidence,
        probabilities={name: confidence},
    )


def test_jev_classifier_maps_response():
    mock_client = MagicMock()
    mock_client.system_one.return_value = MagicMock(
        choices={
            "category": _choice("bug", 0.9),
            "urgency": _choice("p2", 0.8),
            "next_action": _choice("route", 0.85),
            "owner": _choice("Observability", 0.7),
        }
    )

    proposal = JevClassifier(client=mock_client).classify(
        IssueInput(title="Dashboard crash", body="The dashboard fails to load on startup in 9.4.")
    )

    assert proposal.category == "bug"
    assert proposal.urgency == "p2"
    assert proposal.next_action == "route"
    assert proposal.owner == "Observability"
    assert "Jev:" in proposal.reasoning
    assert proposal.observed_signals == ["jev_min_confidence:0.7000"]


def test_jev_classifier_raises_on_api_error():
    mock_client = MagicMock()
    mock_client.system_one.side_effect = TypeSafeAuthenticationError(
        401,
        {"error": "bad key"},
        httpx2.Headers(),
    )

    with pytest.raises(ClassifierError, match="TypeSafe API error"):
        JevClassifier(client=mock_client).classify(
            IssueInput(title="Test", body="Some body long enough for triage.")
        )


def test_jev_classifier_raises_on_missing_answer():
    mock_client = MagicMock()
    mock_client.system_one.return_value = MagicMock(
        choices={"category": _choice("bug", 0.9)}
    )

    with pytest.raises(ClassifierError, match="Missing Jev answer"):
        JevClassifier(client=mock_client).classify(
            IssueInput(title="Test", body="Some body long enough for triage.")
        )


def test_parse_jev_min_confidence():
    assert parse_jev_min_confidence(["jev_min_confidence:0.65"]) == 0.65
    assert parse_jev_min_confidence(["other"]) is None


def test_get_classifier_demo_mode(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert isinstance(get_classifier(demo_mode=True), FakeClassifier)


def test_get_classifier_uses_jev_when_key_set(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("CLASSIFIER", raising=False)
    assert isinstance(get_classifier(demo_mode=False), JevClassifier)


def test_get_classifier_fake_override(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setenv("CLASSIFIER", "fake")
    assert isinstance(get_classifier(demo_mode=False), FakeClassifier)


def test_get_classifier_for_eval_requires_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        get_classifier_for_eval("jev")


def test_intake_records_classifier_failure(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    class BrokenClassifier:
        def classify(self, issue: IssueInput) -> ClassificationProposal:
            raise ClassifierError("API down")

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)
    session = make_session_factory(engine)()
    repo = IssueRepository(session, TriagePipeline(BrokenClassifier()))

    record = repo.intake(
        IssueInput(title="Broken", body="Classifier should fail safely here.")
    )

    assert record.status == "failed"
    assert record.reasoning == "API down"
    session.close()


def test_low_confidence_forces_approval():
    pipeline = TriagePipeline(FakeClassifier(), jev_min_confidence=0.5)

    class LowConfidenceClassifier:
        def classify(self, issue: IssueInput) -> ClassificationProposal:
            return ClassificationProposal(
                category="docs",
                urgency="p3",
                owner="Shared UX",
                next_action="route",
                reasoning="Low confidence route",
                observed_signals=["jev_min_confidence:0.25"],
            )

    pipeline._classifier = LowConfidenceClassifier()
    outcome = pipeline.triage(
        IssueInput(title="Typo in README", body="The word recieve should be receive in docs.")
    )

    assert outcome.requires_approval is True
    assert outcome.workflow_status == "awaiting_approval"
