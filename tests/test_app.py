from fastapi.testclient import TestClient

from issue_triage.app import DEMO_MODE_MESSAGE, create_app


def test_form_intake_vertical_slice(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    client = TestClient(create_app())
    response = client.post(
        "/intake",
        data={
            "title": "Typo in README",
            "body": "The word recieve should be receive in the installation section of the docs.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    issue_id = response.headers["location"].split("/")[-1]

    review = client.get(f"/issues/{issue_id}")
    assert review.status_code == 200
    assert "dry_run_recorded" in review.text or "route" in review.text


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok", "demo_mode": False}


def test_seeds_demo_issues_when_db_empty(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    client = TestClient(create_app())
    home = client.get("/")
    assert home.status_code == 200
    assert "Typo in README" in home.text
    assert "Password reset link still works" in home.text
    assert "App crashes on startup" in home.text


def test_demo_mode_blocks_mutating_paths(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(create_app())

    intake = client.post(
        "/intake",
        data={"title": "New issue", "body": "Some body long enough to triage normally."},
    )
    assert intake.status_code == 403
    assert intake.json()["detail"] == DEMO_MODE_MESSAGE

    home = client.get("/")
    assert "Public demo" in home.text
    assert "Intake is disabled" in home.text

    review = client.get("/issues/2")
    assert review.status_code == 200
    assert "awaiting_approval" in review.text
    version = review.text.split("Version ")[1].split("<")[0].strip()

    approve = client.post(
        "/issues/2/approve",
        data={"version": version, "urgency": "p3", "owner": "Other", "next_action": "route"},
    )
    assert approve.status_code == 403
    assert approve.json()["detail"] == DEMO_MODE_MESSAGE

    reject = client.post("/issues/2/reject", data={"version": version})
    assert reject.status_code == 403
    assert reject.json()["detail"] == DEMO_MODE_MESSAGE


def test_empty_body_intake_via_form(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    client = TestClient(create_app())
    response = client.post(
        "/intake",
        data={"title": "App crashes on startup", "body": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    issue_id = response.headers["location"].split("/")[-1]
    review = client.get(f"/issues/{issue_id}")
    assert review.status_code == 200
    assert "ask_info" in review.text
    assert "EMPTY-001" in review.text


def test_approve_rejects_invalid_urgency(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    client = TestClient(create_app())
    created = client.post(
        "/intake",
        data={
            "title": "Password reset link still works after being used",
            "body": (
                "I used my password reset link, then clicked it again an hour later "
                "and it logged me straight in without asking for a new password."
            ),
        },
        follow_redirects=False,
    )
    issue_id = created.headers["location"].split("/")[-1]
    review = client.get(f"/issues/{issue_id}")
    version = review.text.split('name="version" value="')[1].split('"')[0]

    approve = client.post(
        f"/issues/{issue_id}/approve",
        data={"version": version, "urgency": "32", "owner": "Security", "next_action": "route"},
        follow_redirects=False,
    )
    assert approve.status_code == 303
    assert "error=" in approve.headers["location"]
    assert "awaiting_approval" in client.get(f"/issues/{issue_id}").text


def test_approve_with_valid_edits(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")
    client = TestClient(create_app())
    created = client.post(
        "/intake",
        data={
            "title": "[Dashboards as Code] Soften read response validation",
            "body": "Validation fails when the dashboard has more than 100 panels in version 9.4.",
        },
        follow_redirects=False,
    )
    issue_id = created.headers["location"].split("/")[-1]
    review = client.get(f"/issues/{issue_id}")
    version = review.text.split('name="version" value="')[1].split('"')[0]

    approve = client.post(
        f"/issues/{issue_id}/approve",
        data={"version": version, "urgency": "p2", "owner": "Security", "next_action": "route"},
        follow_redirects=True,
    )
    assert approve.status_code == 200
    assert "dry_run_recorded" in approve.text
    assert "Security" in approve.text


def test_failed_classifier_shows_error_on_review(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "false")

    class BrokenClassifier:
        def classify(self, issue):
            from issue_triage.classifier import ClassifierError

            raise ClassifierError("TypeSafe API error: unauthorized")

    monkeypatch.setattr(
        "issue_triage.app.get_classifier",
        lambda **kwargs: BrokenClassifier(),
    )
    client = TestClient(create_app())

    response = client.post(
        "/intake",
        data={"title": "Broken classifier", "body": "This should fail classifier safely."},
        follow_redirects=False,
    )
    issue_id = response.headers["location"].split("/")[-1]
    review = client.get(f"/issues/{issue_id}")
    assert review.status_code == 200
    assert "Classifier failed" in review.text
    assert "failed" in review.text


def test_health_reports_demo_mode(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok", "demo_mode": True}
