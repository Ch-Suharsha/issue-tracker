from __future__ import annotations

from dataclasses import dataclass

from issue_triage.models import BusinessAction, IssueInput, Urgency

DEFAULT_ASK_INFO_FIELDS = (
    "Steps to reproduce",
    "Expected vs actual behavior",
    "Version / environment",
)


@dataclass(frozen=True)
class AskInfoFields:
    issue_title: str
    requested_fields: tuple[str, ...] = DEFAULT_ASK_INFO_FIELDS


@dataclass(frozen=True)
class DraftReplyFields:
    category: str
    urgency: Urgency
    owner: str
    summary: str | None = None


@dataclass(frozen=True)
class RouteFields:
    category: str
    urgency: Urgency
    owner: str


@dataclass(frozen=True)
class EscalateFields:
    category: str
    urgency: Urgency
    owner: str


def render_ask_info(fields: AskInfoFields) -> str:
    bullets = "\n".join(f"- {item}" for item in fields.requested_fields)
    return (
        "Thanks for the report. Please include:\n"
        f"{bullets}\n\n"
        f"Issue title: {fields.issue_title}"
    )


def render_draft_reply(fields: DraftReplyFields) -> str:
    follow_up = fields.summary or f"We are routing this to {fields.owner} for follow-up."
    return f"Acknowledged as {fields.category} ({fields.urgency}). {follow_up}"


def render_route(fields: RouteFields) -> str:
    return f"Routing to {fields.owner} as {fields.category} with urgency {fields.urgency}."


def render_escalate(fields: EscalateFields) -> str:
    return (
        f"Escalating to {fields.owner} as {fields.category} ({fields.urgency}). "
        "A maintainer will review immediately."
    )


def render_action_comment(
    *,
    action: BusinessAction,
    issue: IssueInput,
    category: str,
    urgency: Urgency,
    owner: str,
) -> str:
    if action == "ask_info":
        return render_ask_info(AskInfoFields(issue_title=issue.title))

    if action == "draft_reply":
        return render_draft_reply(
            DraftReplyFields(category=category, urgency=urgency, owner=owner)
        )

    if action == "route":
        return render_route(RouteFields(category=category, urgency=urgency, owner=owner))

    return render_escalate(
        EscalateFields(category=category, urgency=urgency, owner=owner)
    )
