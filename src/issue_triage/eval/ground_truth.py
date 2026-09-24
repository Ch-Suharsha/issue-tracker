from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

from issue_triage.eval.owner_buckets import category_from_labels, primary_team_bucket
from issue_triage.models import BusinessAction, Urgency

ImpactLabel = Literal["impact:critical", "impact:high", "impact:medium", "impact:low"]

IMPACT_SEVERITY: dict[str, int] = {
    "impact:critical": 4,
    "impact:high": 3,
    "impact:medium": 2,
    "impact:low": 1,
}

URGENCY_FROM_IMPACT: dict[ImpactLabel, Urgency] = {
    "impact:critical": "p1",
    "impact:high": "p2",
    "impact:medium": "p3",
    "impact:low": "p3",
}

# Same vuln patterns as policy.py — used for safety-set membership only.
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


@dataclass(frozen=True)
class GroundTruth:
    impact: ImpactLabel
    urgency: Urgency
    owner: str
    category: Optional[str]
    should_escalate: bool
    has_security_language: bool

    @property
    def requires_security_escalation(self) -> bool:
        return self.has_security_language

    @property
    def requires_critical_routing(self) -> bool:
        return self.impact == "impact:critical" and not self.has_security_language


def primary_impact_label(labels: list[str]) -> Optional[ImpactLabel]:
    impacts = [
        label
        for label in labels
        if label.startswith("impact:") and label != "impact:needs-assessment"
    ]
    if not impacts:
        return None
    return max(impacts, key=lambda label: IMPACT_SEVERITY.get(label, 0))  # type: ignore[return-value]


def matches_security_language(title: str, body: str) -> bool:
    text = f"{title}\n{body}".lower()
    return any(re.search(pattern, text) for pattern in VULNERABILITY_PATTERNS)


def ground_truth_from_record(
    *,
    title: str,
    body: str,
    labels: list[str],
) -> Optional[GroundTruth]:
    impact = primary_impact_label(labels)
    if impact is None:
        return None

    has_security = matches_security_language(title, body)
    urgency = URGENCY_FROM_IMPACT[impact]
    should_escalate = impact == "impact:critical" or has_security

    return GroundTruth(
        impact=impact,
        urgency=urgency,
        owner=primary_team_bucket(labels),
        category=category_from_labels(labels),
        should_escalate=should_escalate,
        has_security_language=has_security,
    )


def reference_action_for(gt: GroundTruth) -> BusinessAction:
    if gt.should_escalate:
        return "escalate"
    if gt.urgency == "p3":
        return "route"
    return "route"
