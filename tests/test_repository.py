import pytest
from sqlalchemy import create_engine

from issue_triage.classifier import FakeClassifier
from issue_triage.db import init_db, make_session_factory
from issue_triage.models import IssueInput
from issue_triage.pipeline import TriagePipeline
from issue_triage.repository import IssueRepository


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)
    session = make_session_factory(engine)()
    repository = IssueRepository(session, TriagePipeline(FakeClassifier()))
    yield repository
    session.close()


def test_intake_persists_and_auto_dry_runs_low_risk(repo: IssueRepository):
    record = repo.intake(
        IssueInput(
            title="Typo in README",
            body="The word recieve should be receive in the installation section of the docs.",
        )
    )

    assert record.id is not None
    assert record.status == "dry_run_recorded"
    assert record.dry_run is not None
    reloaded = repo.get(record.id)
    assert reloaded is not None
    assert reloaded.status == "dry_run_recorded"


def test_ask_info_auto_proceeds_with_template(repo: IssueRepository):
    record = repo.intake(IssueInput(title="App crashes on startup", body=""))

    assert record.status == "dry_run_recorded"
    assert record.dry_run is not None
    assert record.dry_run.action == "ask_info"
    assert "Steps to reproduce" in record.dry_run.comment_body
    assert "Issue title: App crashes on startup" in record.dry_run.comment_body


def test_escalation_waits_for_approval(repo: IssueRepository):
    record = repo.intake(
        IssueInput(
            title="Password reset link still works after being used",
            body=(
                "I used my password reset link, then clicked it again an hour later "
                "and it logged me straight in without asking for a new password."
            ),
        )
    )

    assert record.status == "awaiting_approval"
    approved = repo.approve(record.id, expected_version=record.version)
    assert approved.status == "dry_run_recorded"
    assert approved.dry_run is not None
    assert approved.dry_run.action == "escalate"
