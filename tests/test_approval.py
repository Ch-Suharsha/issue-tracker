from issue_triage.approval import approval_policy_for
from issue_triage.models import PolicyDecision


def test_ask_info_p3_auto_proceeds():
    requires, kind = approval_policy_for(
        urgency="p3",
        next_action="ask_info",
        policy=PolicyDecision(applied=True, rule_id="EMPTY-001", next_action="ask_info"),
    )
    assert requires is False
    assert kind == "auto_execute"


def test_route_p3_auto_proceeds():
    requires, kind = approval_policy_for(
        urgency="p3",
        next_action="route",
        policy=PolicyDecision(applied=False),
    )
    assert requires is False
    assert kind == "auto_execute"


def test_escalate_always_requires_approval():
    requires, kind = approval_policy_for(
        urgency="p1",
        next_action="escalate",
        policy=PolicyDecision(
            applied=True,
            rule_id="SEC-001",
            next_action="escalate",
            urgency="p1",
        ),
    )
    assert requires is True
    assert kind == "require_approval"


def test_p1_always_requires_approval_even_for_route():
    requires, kind = approval_policy_for(
        urgency="p1",
        next_action="route",
        policy=PolicyDecision(applied=False),
    )
    assert requires is True
    assert kind == "require_approval"


def test_low_jev_confidence_forces_approval():
    requires, kind = approval_policy_for(
        urgency="p3",
        next_action="route",
        policy=PolicyDecision(applied=False),
        model_min_confidence=0.3,
        min_confidence_threshold=0.5,
    )
    assert requires is True
    assert kind == "require_approval"


def test_draft_reply_p3_requires_approval():
    requires, kind = approval_policy_for(
        urgency="p3",
        next_action="draft_reply",
        policy=PolicyDecision(applied=False),
    )
    assert requires is True
    assert kind == "require_approval"
