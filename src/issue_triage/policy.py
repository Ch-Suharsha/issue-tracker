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


def _matches_vulnerability_language(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in VULNERABILITY_PATTERNS)


def apply_policy(
    issue: IssueInput, proposal: ClassificationProposal
) -> tuple[ClassificationProposal, PolicyDecision]:
    text = f"{issue.title}\n{issue.body}".strip()

    if len(issue.body.strip()) < MIN_BODY_CHARS:
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
    return {
        "category": policy.category or proposal.category,
        "urgency": policy.urgency or proposal.urgency,
        "owner": policy.owner or proposal.owner,
        "next_action": policy.next_action or proposal.next_action,
        "reasoning": proposal.reasoning,
    }
