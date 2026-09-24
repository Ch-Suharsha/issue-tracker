from issue_triage.classifier import FakeClassifier
from issue_triage.models import IssueInput
from issue_triage.pipeline import TriagePipeline


def test_empty_body_forces_ask_info():
    pipeline = TriagePipeline(FakeClassifier())
    outcome = pipeline.triage(IssueInput(title="App crashes", body=""))

    assert outcome.next_action == "ask_info"
    assert outcome.policy.applied is True
    assert outcome.policy.rule_id == "EMPTY-001"


def test_empty_body_preserves_escalate_proposal():
    from issue_triage.classifier import ClassificationProposal
    from issue_triage.models import IssueInput
    from issue_triage.pipeline import TriagePipeline

    class EscalatingClassifier:
        def classify(self, issue: IssueInput) -> ClassificationProposal:
            return ClassificationProposal(
                category="bug",
                urgency="p1",
                owner="Security",
                next_action="escalate",
                reasoning="test stub",
            )

    pipeline = TriagePipeline(EscalatingClassifier())
    outcome = pipeline.triage(IssueInput(title="Auth bypass in login", body=""))

    assert outcome.next_action == "escalate"
    assert outcome.urgency == "p1"
    assert outcome.policy.rule_id == "EMPTY-001"


def test_security_language_overrides_model_to_escalate():
    pipeline = TriagePipeline(FakeClassifier())
    issue = IssueInput(
        title="Password reset link still works after being used",
        body=(
            "I used my password reset link, then clicked it again an hour later "
            "and it logged me straight in without asking for a new password."
        ),
    )
    outcome = pipeline.triage(issue)

    assert outcome.next_action == "escalate"
    assert outcome.urgency == "p1"
    assert outcome.policy.rule_id == "SEC-001"
    assert outcome.requires_approval is True


def test_low_risk_docs_route_may_auto_proceed():
    pipeline = TriagePipeline(FakeClassifier())
    issue = IssueInput(
        title="Typo in README",
        body="The word recieve should be receive in the installation section of the docs.",
    )
    outcome = pipeline.triage(issue)

    assert outcome.next_action == "route"
    assert outcome.urgency == "p3"
    assert outcome.requires_approval is False


def test_demo_mode_always_requires_approval():
    pipeline = TriagePipeline(FakeClassifier(), demo_mode=True)
    issue = IssueInput(
        title="Typo in README",
        body="The word recieve should be receive in the installation section of the docs.",
    )
    outcome = pipeline.triage(issue)

    assert outcome.requires_approval is True
