from __future__ import annotations

from issue_triage.models import ApprovalPolicyKind, BusinessAction, PolicyDecision, Urgency


def approval_policy_for(
    *,
    urgency: Urgency,
    next_action: BusinessAction,
    policy: PolicyDecision,
    demo_mode: bool = False,
    model_min_confidence: float | None = None,
    min_confidence_threshold: float | None = None,
) -> tuple[bool, ApprovalPolicyKind]:
    if demo_mode:
        return True, "require_approval"

    if (
        min_confidence_threshold is not None
        and model_min_confidence is not None
        and model_min_confidence < min_confidence_threshold
    ):
        return True, "require_approval"

    if policy.applied and policy.next_action == "escalate":
        return True, "require_approval"

    if next_action == "escalate" or urgency == "p1":
        return True, "require_approval"

    if next_action == "ask_info" and urgency == "p3":
        return False, "auto_execute"

    if next_action == "route" and urgency == "p3":
        return False, "auto_execute"

    return True, "require_approval"
