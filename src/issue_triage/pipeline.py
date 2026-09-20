from __future__ import annotations

from issue_triage.approval import approval_policy_for
from issue_triage.classifier import Classifier, parse_jev_min_confidence
from issue_triage.models import DryRunAction, IssueInput, TriageOutcome, WorkflowStatus
from issue_triage.policy import apply_policy, merge_proposal
from issue_triage.templates import render_action_comment


class TriagePipeline:
    def __init__(
        self,
        classifier: Classifier,
        *,
        demo_mode: bool = False,
        jev_min_confidence: float | None = None,
    ) -> None:
        self._classifier = classifier
        self._demo_mode = demo_mode
        self._jev_min_confidence = jev_min_confidence

    def triage(self, issue: IssueInput) -> TriageOutcome:
        proposal = self._classifier.classify(issue)
        adjusted, policy = apply_policy(issue, proposal)
        merged = merge_proposal(adjusted, policy)

        requires_approval, approval_kind = approval_policy_for(
            urgency=merged["urgency"],
            next_action=merged["next_action"],
            policy=policy,
            demo_mode=self._demo_mode,
            model_min_confidence=parse_jev_min_confidence(proposal.observed_signals),
            min_confidence_threshold=self._jev_min_confidence,
        )

        status: WorkflowStatus = (
            "awaiting_approval" if requires_approval else "classified"
        )

        return TriageOutcome(
            category=merged["category"],
            urgency=merged["urgency"],
            owner=merged["owner"],
            next_action=merged["next_action"],
            reasoning=merged["reasoning"],
            policy=policy,
            requires_approval=requires_approval,
            approval_policy=approval_kind,
            workflow_status=status,
        )

    def build_dry_run(self, issue: IssueInput, outcome: TriageOutcome) -> DryRunAction:
        comment = render_action_comment(
            action=outcome.next_action,
            issue=issue,
            category=outcome.category,
            urgency=outcome.urgency,
            owner=outcome.owner,
        )
        labels = [outcome.category, f"urgency:{outcome.urgency}"]
        if outcome.policy.applied:
            labels.append(f"policy:{outcome.policy.rule_id}")

        return DryRunAction(
            comment_body=comment,
            labels=labels,
            owner=outcome.owner,
            action=outcome.next_action,
        )
