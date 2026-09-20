from __future__ import annotations

from sqlalchemy.orm import Session

from issue_triage.db import DecisionLogRow, IssueWorkflowRow
from issue_triage.classifier import ClassifierError
from issue_triage.models import (
    BusinessAction,
    DryRunAction,
    IssueInput,
    TriageOutcome,
    TriageRecord,
    Urgency,
)
from issue_triage.pipeline import TriagePipeline


class ConcurrencyError(Exception):
    pass


class InvalidTriageFieldsError(Exception):
    pass


def _validate_urgency(value: str) -> Urgency:
    if value not in ("p1", "p2", "p3"):
        raise InvalidTriageFieldsError(
            f"Urgency must be p1, p2, or p3 (got {value!r})."
        )
    return value  # type: ignore[return-value]


def _validate_next_action(value: str) -> BusinessAction:
    if value not in ("ask_info", "draft_reply", "route", "escalate"):
        raise InvalidTriageFieldsError(
            "Action must be ask_info, draft_reply, route, or escalate "
            f"(got {value!r})."
        )
    return value  # type: ignore[return-value]


class IssueRepository:
    def __init__(self, session: Session, pipeline: TriagePipeline) -> None:
        self._session = session
        self._pipeline = pipeline

    def _to_record(self, row: IssueWorkflowRow) -> TriageRecord:
        dry_run = None
        if row.dry_run_action:
            dry_run = DryRunAction(
                comment_body=row.dry_run_comment or "",
                labels=(row.dry_run_labels or "").split(",") if row.dry_run_labels else [],
                owner=row.dry_run_owner or "",
                action=row.dry_run_action,  # type: ignore[arg-type]
            )

        return TriageRecord(
            id=row.id,
            title=row.title,
            body=row.body,
            source_url=row.source_url,
            status=row.status,  # type: ignore[arg-type]
            version=row.version,
            category=row.category,
            urgency=row.urgency,  # type: ignore[arg-type]
            owner=row.owner,
            next_action=row.next_action,  # type: ignore[arg-type]
            reasoning=row.reasoning,
            policy_rule_id=row.policy_rule_id,
            policy_reason=row.policy_reason,
            requires_approval=row.requires_approval,
            approval_policy=row.approval_policy,  # type: ignore[arg-type]
            dry_run=dry_run,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _log(self, row: IssueWorkflowRow, event: str, detail: str, actor: str = "system") -> None:
        self._session.add(
            DecisionLogRow(issue_id=row.id, event=event, detail=detail, actor=actor)
        )

    def find_by_source_url(self, source_url: str) -> TriageRecord | None:
        row = (
            self._session.query(IssueWorkflowRow)
            .filter(IssueWorkflowRow.source_url == source_url)
            .one_or_none()
        )
        return self._to_record(row) if row else None

    def intake(self, issue: IssueInput) -> TriageRecord:
        if issue.source_url:
            existing = self.find_by_source_url(issue.source_url)
            if existing is not None:
                return existing

        row = IssueWorkflowRow(
            title=issue.title,
            body=issue.body,
            source_url=issue.source_url,
            status="received",
        )
        self._session.add(row)
        self._session.flush()
        detail = f"Received issue: {issue.title}"
        if issue.source_url:
            detail = f"Imported from {issue.source_url}: {issue.title}"
        self._log(row, "intake", detail)

        try:
            outcome = self._pipeline.triage(issue)
        except ClassifierError as exc:
            row.status = "failed"
            row.reasoning = str(exc)
            row.version += 1
            self._log(row, "classifier_failed", str(exc))
            self._session.commit()
            self._session.refresh(row)
            return self._to_record(row)

        row.category = outcome.category
        row.urgency = outcome.urgency
        row.owner = outcome.owner
        row.next_action = outcome.next_action
        row.reasoning = outcome.reasoning
        row.policy_rule_id = outcome.policy.rule_id
        row.policy_reason = outcome.policy.reason
        row.requires_approval = outcome.requires_approval
        row.approval_policy = outcome.approval_policy
        row.status = outcome.workflow_status
        row.version += 1

        policy_note = (
            f"Policy {outcome.policy.rule_id}: {outcome.policy.reason}"
            if outcome.policy.applied
            else "No policy override"
        )
        self._log(row, "classified", policy_note)

        if not outcome.requires_approval:
            dry_run = self._pipeline.build_dry_run(issue, outcome)
            self._apply_dry_run(row, dry_run, actor="system")

        self._session.commit()
        self._session.refresh(row)
        return self._to_record(row)

    def get(self, issue_id: int) -> TriageRecord | None:
        row = self._session.get(IssueWorkflowRow, issue_id)
        return self._to_record(row) if row else None

    def list_recent(self, limit: int = 20) -> list[TriageRecord]:
        rows = (
            self._session.query(IssueWorkflowRow)
            .order_by(IssueWorkflowRow.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_record(row) for row in rows]

    def approve(
        self,
        issue_id: int,
        *,
        expected_version: int,
        urgency: str | None = None,
        owner: str | None = None,
        next_action: str | None = None,
        actor: str = "triager",
    ) -> TriageRecord:
        row = self._session.get(IssueWorkflowRow, issue_id)
        if row is None:
            raise KeyError(f"Issue {issue_id} not found")
        if row.version != expected_version:
            raise ConcurrencyError("Issue was updated by someone else")

        resolved_urgency = _validate_urgency(urgency or row.urgency or "p3")
        resolved_action = _validate_next_action(next_action or row.next_action or "route")
        row.urgency = resolved_urgency
        if owner:
            row.owner = owner.strip()
        row.next_action = resolved_action

        issue = IssueInput(title=row.title, body=row.body)
        outcome = TriageOutcome(
            category=row.category or "unknown",
            urgency=resolved_urgency,
            owner=row.owner or "Other",
            next_action=resolved_action,
            reasoning=row.reasoning or "",
            policy=self._policy_from_row(row),
            requires_approval=False,
            approval_policy="auto_execute",  # type: ignore[arg-type]
            workflow_status="approved",
        )
        dry_run = self._pipeline.build_dry_run(issue, outcome)
        row.status = "approved"
        row.version += 1
        self._log(row, "approved", "Triager approved proposal", actor=actor)
        self._apply_dry_run(row, dry_run, actor=actor)
        self._session.commit()
        self._session.refresh(row)
        return self._to_record(row)

    def reject(self, issue_id: int, *, expected_version: int, actor: str = "triager") -> TriageRecord:
        row = self._session.get(IssueWorkflowRow, issue_id)
        if row is None:
            raise KeyError(f"Issue {issue_id} not found")
        if row.version != expected_version:
            raise ConcurrencyError("Issue was updated by someone else")

        row.status = "rejected"
        row.version += 1
        self._log(row, "rejected", "Triager rejected proposal", actor=actor)
        self._session.commit()
        self._session.refresh(row)
        return self._to_record(row)

    def _apply_dry_run(self, row: IssueWorkflowRow, dry_run: DryRunAction, actor: str) -> None:
        row.dry_run_comment = dry_run.comment_body
        row.dry_run_labels = ",".join(dry_run.labels)
        row.dry_run_owner = dry_run.owner
        row.dry_run_action = dry_run.action
        row.status = "dry_run_recorded"
        row.version += 1
        self._log(
            row,
            "dry_run",
            f"Would post comment and labels: {dry_run.labels}",
            actor=actor,
        )

    def _policy_from_row(self, row: IssueWorkflowRow):
        from issue_triage.models import PolicyDecision

        return PolicyDecision(
            applied=bool(row.policy_rule_id),
            rule_id=row.policy_rule_id,
            reason=row.policy_reason,
        )
