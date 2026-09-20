from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from issue_triage.app import create_app
from issue_triage.classifier import FakeClassifier
from issue_triage.db import init_db, make_session_factory
from issue_triage.github import (
    GitHubFetchError,
    GitHubIssueRef,
    HttpxGitHubClient,
    parse_github_ref,
)
from issue_triage.models import IssueInput
from issue_triage.pipeline import TriagePipeline
from issue_triage.repository import IssueRepository


def test_parse_github_url():
    ref = parse_github_ref("https://github.com/elastic/kibana/issues/12345")
    assert ref == GitHubIssueRef(owner="elastic", repo="kibana", number=12345)
    assert ref.source_url == "https://github.com/elastic/kibana/issues/12345"


def test_parse_github_short_ref():
    ref = parse_github_ref("elastic/kibana#99")
    assert ref.owner == "elastic"
    assert ref.repo == "kibana"
    assert ref.number == 99


def test_parse_invalid_ref_raises():
    with pytest.raises(GitHubFetchError, match="Invalid GitHub reference"):
        parse_github_ref("not-a-ref")


def test_fetch_issue_success():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"title": "Typo in README", "body": "recieve should be receive"},
        )
    )
    client = HttpxGitHubClient(client=httpx.Client(transport=transport))
    content = client.fetch_issue(GitHubIssueRef("elastic", "kibana", 1))

    assert content.title == "Typo in README"
    assert content.body == "recieve should be receive"
    assert content.source_url == "https://github.com/elastic/kibana/issues/1"


def test_fetch_issue_not_found():
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    client = HttpxGitHubClient(client=httpx.Client(transport=transport))

    with pytest.raises(GitHubFetchError, match="Issue not found"):
        client.fetch_issue(GitHubIssueRef("elastic", "kibana", 999))


def test_intake_deduplicates_by_source_url():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)
    session = make_session_factory(engine)()
    repo = IssueRepository(session, TriagePipeline(FakeClassifier()))

    first = repo.intake(
        IssueInput(
            title="Typo in README",
            body="The word recieve should be receive in the installation section.",
            source_url="https://github.com/elastic/kibana/issues/42",
        )
    )
    second = repo.intake(
        IssueInput(
            title="Typo in README",
            body="The word recieve should be receive in the installation section.",
            source_url="https://github.com/elastic/kibana/issues/42",
        )
    )

    assert first.id == second.id
    session.close()


def test_github_import_route_mocked(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    mock_client = MagicMock()
    mock_client.fetch_issue.return_value = MagicMock(
        title="Typo in README",
        body="The word recieve should be receive in the installation section of the docs.",
        source_url="https://github.com/elastic/kibana/issues/100",
    )

    monkeypatch.setattr(
        "issue_triage.app.HttpxGitHubClient",
        lambda **kwargs: mock_client,
    )

    client = TestClient(create_app())
    response = client.post(
        "/intake/github",
        data={"github_ref": "elastic/kibana#100"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    issue_id = response.headers["location"].split("/")[-1]
    review = client.get(f"/issues/{issue_id}")
    assert review.status_code == 200
    assert "Typo in README" in review.text


def test_github_import_failure_shows_error(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    mock_client = MagicMock()
    mock_client.fetch_issue.side_effect = GitHubFetchError("Issue not found: elastic/kibana#999")

    monkeypatch.setattr(
        "issue_triage.app.HttpxGitHubClient",
        lambda **kwargs: mock_client,
    )

    client = TestClient(create_app())
    response = client.post(
        "/intake/github",
        data={"github_ref": "elastic/kibana#999"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Import failed" in response.text
    assert "Issue not found" in response.text
    assert "/issues/" not in response.url.path or response.url.path == "/"
