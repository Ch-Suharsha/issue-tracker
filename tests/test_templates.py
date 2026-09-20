from issue_triage.models import IssueInput
from issue_triage.templates import (
    AskInfoFields,
    DraftReplyFields,
    render_action_comment,
    render_ask_info,
    render_draft_reply,
)


def test_ask_info_uses_structured_fields():
    body = render_ask_info(
        AskInfoFields(
            issue_title="App crashes on launch",
            requested_fields=("Steps to reproduce", "Logs"),
        )
    )

    assert "Steps to reproduce" in body
    assert "Logs" in body
    assert "Issue title: App crashes on launch" in body


def test_draft_reply_uses_structured_fields():
    body = render_draft_reply(
        DraftReplyFields(
            category="bug",
            urgency="p2",
            owner="Observability",
            summary="We will investigate the dashboard timeout.",
        )
    )

    assert "Acknowledged as bug (p2)" in body
    assert "We will investigate the dashboard timeout." in body


def test_render_action_comment_delegates_to_structured_templates():
    ask = render_action_comment(
        action="ask_info",
        issue=IssueInput(title="Short", body=""),
        category="unknown",
        urgency="p3",
        owner="Other",
    )
    assert "Issue title: Short" in ask

    draft = render_action_comment(
        action="draft_reply",
        issue=IssueInput(title="Bug", body="Something broke"),
        category="bug",
        urgency="p2",
        owner="Observability",
    )
    assert "Acknowledged as bug (p2)" in draft
    assert "Observability" in draft
