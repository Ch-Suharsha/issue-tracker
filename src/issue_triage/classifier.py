from __future__ import annotations

from typing import Protocol

from issue_triage.models import ClassificationProposal, IssueInput


class ClassifierError(Exception):
    """Raised when the Classifier cannot produce a valid proposal."""


def parse_jev_min_confidence(observed_signals: list[str]) -> float | None:
    for signal in observed_signals:
        if signal.startswith("jev_min_confidence:"):
            try:
                return float(signal.split(":", 1)[1])
            except ValueError:
                return None
    return None


class Classifier(Protocol):
    def classify(self, issue: IssueInput) -> ClassificationProposal: ...


class FakeClassifier:
    """Deterministic Classifier for tests and local dev without an LLM."""

    def classify(self, issue: IssueInput) -> ClassificationProposal:
        body = issue.body.strip().lower()
        title = issue.title.strip().lower()

        if not body or len(body) < 20:
            return ClassificationProposal(
                category="unknown",
                urgency="p3",
                owner="Other",
                next_action="ask_info",
                reasoning="Body is empty or too short to triage reliably.",
            )

        if "typo" in title or "readme" in title:
            return ClassificationProposal(
                category="docs",
                urgency="p3",
                owner="Shared UX",
                next_action="route",
                reasoning="Looks like a documentation typo.",
            )

        if "password reset" in body or "auth bypass" in body:
            return ClassificationProposal(
                category="bug",
                urgency="p3",
                owner="Other",
                next_action="route",
                reasoning="Security-related wording but model scored routine.",
            )

        return ClassificationProposal(
            category="bug",
            urgency="p2",
            owner="Observability",
            next_action="route",
            reasoning="Default bug routing for demo.",
        )
