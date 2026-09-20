from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from issue_triage.classifier_factory import get_classifier, get_jev_min_confidence
from issue_triage.db import init_db, make_engine, make_session_factory
from issue_triage.github import GitHubFetchError, HttpxGitHubClient, parse_github_ref
from issue_triage.models import IssueInput
from issue_triage.pipeline import TriagePipeline
from issue_triage.repository import ConcurrencyError, InvalidTriageFieldsError, IssueRepository
from issue_triage.seed import seed_if_empty

TEMPLATES_DIR = Path(__file__).parent / "web_templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

DEMO_MODE_MESSAGE = (
    "This public demo is read-only. Browse the seeded examples below — "
    "intake and approval are disabled to protect demo data and API quota."
)


def create_app() -> FastAPI:
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    engine = make_engine()
    init_db(engine)
    session_factory = make_session_factory(engine)
    pipeline = TriagePipeline(
        get_classifier(demo_mode=demo_mode),
        demo_mode=demo_mode,
        jev_min_confidence=get_jev_min_confidence(),
    )
    seed_if_empty(session_factory, pipeline)

    app = FastAPI(title="Issue Triage", version="0.1.0")

    @contextmanager
    def repo_scope():
        session = session_factory()
        try:
            yield IssueRepository(session, pipeline)
        finally:
            session.close()

    github_client = HttpxGitHubClient(token=os.getenv("GITHUB_TOKEN"))

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, error: str | None = None):
        with repo_scope() as repo:
            issues = repo.list_recent()
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                "issues": issues,
                "demo_mode": demo_mode,
                "demo_mode_message": DEMO_MODE_MESSAGE,
                "error": error,
            },
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "demo_mode": demo_mode}

    @app.post("/intake")
    def intake(title: str = Form(...), body: str = Form(default="")):
        if demo_mode:
            raise HTTPException(status_code=403, detail=DEMO_MODE_MESSAGE)

        issue = IssueInput(title=title.strip(), body=body.strip())
        with repo_scope() as repo:
            record = repo.intake(issue)
        return RedirectResponse(url=f"/issues/{record.id}", status_code=303)

    @app.post("/intake/github")
    def intake_github(github_ref: str = Form(...)):
        if demo_mode:
            raise HTTPException(status_code=403, detail=DEMO_MODE_MESSAGE)

        try:
            ref = parse_github_ref(github_ref)
            content = github_client.fetch_issue(ref)
        except GitHubFetchError as exc:
            return RedirectResponse(
                url=f"/?error={quote(str(exc))}",
                status_code=303,
            )

        issue = IssueInput(
            title=content.title,
            body=content.body,
            source_url=content.source_url,
        )
        with repo_scope() as repo:
            record = repo.intake(issue)
        return RedirectResponse(url=f"/issues/{record.id}", status_code=303)

    @app.get("/issues/{issue_id}", response_class=HTMLResponse)
    def review_issue(request: Request, issue_id: int, error: str | None = None):
        with repo_scope() as repo:
            record = repo.get(issue_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Issue not found")
        return templates.TemplateResponse(
            request,
            "review.html",
            {
                "issue": record,
                "demo_mode": demo_mode,
                "demo_mode_message": DEMO_MODE_MESSAGE,
                "error": error,
            },
        )

    @app.post("/issues/{issue_id}/approve")
    def approve_issue(
        issue_id: int,
        version: int = Form(...),
        urgency: str = Form(None),
        owner: str = Form(None),
        next_action: str = Form(None),
    ):
        if demo_mode:
            raise HTTPException(status_code=403, detail=DEMO_MODE_MESSAGE)

        with repo_scope() as repo:
            try:
                record = repo.approve(
                    issue_id,
                    expected_version=version,
                    urgency=urgency or None,
                    owner=owner or None,
                    next_action=next_action or None,
                )
            except InvalidTriageFieldsError as exc:
                return RedirectResponse(
                    url=f"/issues/{issue_id}?error={quote(str(exc))}",
                    status_code=303,
                )
            except ConcurrencyError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(url=f"/issues/{record.id}", status_code=303)

    @app.post("/issues/{issue_id}/reject")
    def reject_issue(issue_id: int, version: int = Form(...)):
        if demo_mode:
            raise HTTPException(status_code=403, detail=DEMO_MODE_MESSAGE)

        with repo_scope() as repo:
            try:
                record = repo.reject(issue_id, expected_version=version)
            except ConcurrencyError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(url=f"/issues/{record.id}", status_code=303)

    return app
