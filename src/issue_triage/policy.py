from __future__ import annotations

import re

from issue_triage.models import (
    BusinessAction,
    ClassificationProposal,
    IssueInput,
    PolicyDecision,
    Urgency,
)

VULNERABILITY_PATTERNS = [
    r"auth bypass",
    r"password reset",
    r"privilege escalation",
    r"\bxss\b",
    r"credential",
    r"cross[- ]tenant",
    r"visible in a newly created space",
    r"visible across",
    r"data leak",
    r"session fixation",
    r"injection",
]

MIN_BODY_CHARS = 20

_URGENCY_RANK: dict[Urgency, int] = {"p3": 0, "p2": 1, "p1": 2}


def _matches_vulnerability_language(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in VULNERABILITY_PATTERNS)


def _max_urgency(current: Urgency, proposed: Urgency) -> Urgency:
    return current if _URGENCY_RANK[current] >= _URGENCY_RANK[proposed] else proposed


def _is_high_stakes(proposal: ClassificationProposal) -> bool:
    return proposal.next_action == "escalate" or proposal.urgency == "p1"


def _empty_body_policy(
    issue: IssueInput, proposal: ClassificationProposal
) -> tuple[ClassificationProposal, PolicyDecision]:
    if _is_high_stakes(proposal):
        return (
            proposal,
            PolicyDecision(
                applied=True,
                rule_id="EMPTY-001",
                reason="Issue body is short; preserving high-stakes classifier proposal.",
            ),
        )

    return (
        ClassificationProposal(
            category=proposal.category,
            urgency="p3",
            owner=proposal.owner,
            next_action="ask_info",
            reasoning=proposal.reasoning,
            observed_signals=proposal.observed_signals,
        ),
        PolicyDecision(
            applied=True,
            rule_id="EMPTY-001",
            reason="Issue body is too short to act on; ask for reproduction details.",
            next_action="ask_info",
            urgency="p3",
        ),
    )


def apply_policy(
    issue: IssueInput, proposal: ClassificationProposal
) -> tuple[ClassificationProposal, PolicyDecision]:
    text = f"{issue.title}\n{issue.body}".strip()

    if len(issue.body.strip()) < MIN_BODY_CHARS:
        return _empty_body_policy(issue, proposal)

    if _matches_vulnerability_language(text):
        return (
            ClassificationProposal(
                category="bug",
                urgency="p1",
                owner="Security",
                next_action="escalate",
                reasoning=proposal.reasoning,
                observed_signals=proposal.observed_signals,
            ),
            PolicyDecision(
                applied=True,
                rule_id="SEC-001",
                reason="Vulnerability-language signal detected; mandatory escalation.",
                category="bug",
                urgency="p1",
                owner="Security",
                next_action="escalate",
            ),
        )

    return (proposal, PolicyDecision(applied=False))


def merge_proposal(proposal: ClassificationProposal, policy: PolicyDecision) -> dict:
    merged_urgency = policy.urgency or proposal.urgency
    merged_action: BusinessAction = policy.next_action or proposal.next_action

    if policy.urgency and policy.next_action:
        merged_urgency = _max_urgency(proposal.urgency, policy.urgency)
    elif policy.urgency:
        merged_urgency = _max_urgency(proposal.urgency, policy.urgency)
    elif policy.next_action == "escalate":
        merged_urgency = _max_urgency(proposal.urgency, "p1")

    if proposal.next_action == "escalate" and merged_action != "escalate":
        merged_action = "escalate"
    if proposal.urgency == "p1" and merged_urgency == "p3" and merged_action == "ask_info":
        merged_action = proposal.next_action
        merged_urgency = proposal.urgency

    return {
        "category": policy.category or proposal.category,
        "urgency": merged_urgency,
        "owner": policy.owner or proposal.owner,
        "next_action": merged_action,
        "reasoning": proposal.reasoning,
    }
