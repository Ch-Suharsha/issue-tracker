from __future__ import annotations

import re
from typing import Optional

# Canonical owner buckets (~10 groups) for routing evaluation.
OWNER_BUCKETS: tuple[str, ...] = (
    "Security",
    "Observability",
    "Dashboards",
    "Fleet",
    "Search",
    "Shared UX",
    "Platform",
    "ML & AI",
    "Docs",
    "Other",
)

# Map normalized Team:* label suffixes to owner buckets.
# Keys are lowercased, DEPRECATED stripped, leading "Team:" removed.
TEAM_TO_BUCKET: dict[str, str] = {
    # Security (~1.7k+ issues)
    "securitysolution": "Security",
    "security": "Security",
    "threat hunting": "Security",
    "threat hunting:investigations": "Security",
    "defend workflows": "Security",
    "entity analytics": "Security",
    "security generative ai": "Security",
    "detection engineering": "Security",
    "cloud security": "Security",
    "cases": "Security",
    "responseops": "Security",
    "siem": "Security",
    # Observability
    "obs-ux-infra_services": "Observability",
    "obs-onboarding": "Observability",
    "obs-presentation": "Observability",
    "obs-signals-logs": "Observability",
    "obs-signals-metrics": "Observability",
    "obs-exploration": "Observability",
    "obs-knowledge": "Observability",
    "actionable-obs": "Observability",
    "actionable observability": "Observability",
    "observability": "Observability",
    "unified observability": "Observability",
    "logstash": "Observability",
    "uptime": "Observability",
    "apm": "Observability",
    "infra monitoring ui": "Observability",
    # Dashboards / Presentation
    "presentation": "Dashboards",
    "visualizations": "Dashboards",
    # Fleet / Agent
    "fleet": "Fleet",
    "elastic-agent-control-plane": "Fleet",
    "agent": "Fleet",
    "asset mgmt": "Fleet",
    "asset management": "Fleet",
    # Search / Discovery
    "search": "Search",
    "datadiscovery": "Search",
    "esql": "Search",
    "enterprisesearch": "Search",
    "discover": "Search",
    # Shared UX
    "sharedux": "Shared UX",
    "platform-design": "Shared UX",
    # Platform / Management
    "kibana management": "Platform",
    "core": "Platform",
    "core analysis": "Platform",
    "automatic migrations": "Platform",
    "integration-experience": "Platform",
    "integrations": "Platform",
    "cloud": "Platform",
    "operations": "Platform",
    "one workflow": "Platform",
    "workchat": "Platform",
    "journey/onboarding": "Platform",
    "streams-ui": "Platform",
    "geo": "Platform",
    "qa": "Platform",
    # ML & AI
    "ml": "ML & AI",
    "ai infra": "ML & AI",
    "agent-builder": "ML & AI",
    # Docs
    "docs": "Docs",
}


def normalize_team_label(label: str) -> str:
    """Strip Team: prefix, DEPRECATED markers, and normalize whitespace."""
    text = label
    if text.lower().startswith("team:"):
        text = text[5:]
    text = re.sub(r"\s*-\s*deprecated\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*deprecated\s*$", "", text, flags=re.IGNORECASE)
    return text.strip().lower()


def team_label_to_bucket(label: str) -> str:
    normalized = normalize_team_label(label)
    return TEAM_TO_BUCKET.get(normalized, "Other")


def primary_team_bucket(labels: list[str]) -> str:
    """Pick the owner bucket from Team:* labels; first match wins."""
    team_labels = [label for label in labels if label.startswith("Team:")]
    if not team_labels:
        return "Other"
    return team_label_to_bucket(team_labels[0])


def category_from_labels(labels: list[str]) -> Optional[str]:
    for candidate in ("bug", "enhancement", "docs", "question"):
        if candidate in labels:
            return candidate
    return None
