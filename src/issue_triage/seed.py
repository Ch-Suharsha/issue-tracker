from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from issue_triage.models import IssueInput
from issue_triage.pipeline import TriagePipeline
from issue_triage.repository import IssueRepository

DEMO_ISSUES: tuple[IssueInput, ...] = (
    IssueInput(
        title="Typo in README",
        body=(
            "The word recieve should be receive in the installation section of the docs."
        ),
    ),
    IssueInput(
        title="Password reset link still works after being used",
        body=(
            "I used my password reset link, then clicked it again an hour later "
            "and it logged me straight in without asking for a new password."
        ),
    ),
    IssueInput(
        title="App crashes on startup",
        body="",
    ),
)


def seed_if_empty(session_factory: sessionmaker, pipeline: TriagePipeline) -> int:
    """Insert demo issues when the workflow table is empty (first load / fresh deploy)."""
    session = session_factory()
    try:
        repo = IssueRepository(session, pipeline)
        if repo.list_recent(limit=1):
            return 0

        for issue in DEMO_ISSUES:
            repo.intake(issue)
        return len(DEMO_ISSUES)
    finally:
        session.close()
