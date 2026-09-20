from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

BusinessAction = Literal["ask_info", "draft_reply", "route", "escalate"]
Urgency = Literal["p1", "p2", "p3"]
WorkflowStatus = Literal[
    "received",
    "classified",
    "awaiting_approval",
    "approved",
    "rejected",
    "dry_run_recorded",
    "failed",
]
ApprovalPolicyKind = Literal["auto_execute", "require_approval", "prohibit_auto"]


class IssueInput(BaseModel):
    title: str
    body: str
    author_type: Optional[str] = None
    source_url: Optional[str] = None


class ClassificationProposal(BaseModel):
    category: str
    urgency: Urgency
    owner: str
    next_action: BusinessAction
    reasoning: str
    observed_signals: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    applied: bool = False
    rule_id: Optional[str] = None
    reason: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[Urgency] = None
    owner: Optional[str] = None
    next_action: Optional[BusinessAction] = None


class TriageOutcome(BaseModel):
    category: str
    urgency: Urgency
    owner: str
    next_action: BusinessAction
    reasoning: str
    policy: PolicyDecision
    requires_approval: bool
    approval_policy: ApprovalPolicyKind
    workflow_status: WorkflowStatus


class DryRunAction(BaseModel):
    comment_body: str
    labels: list[str]
    owner: str
    action: BusinessAction


class TriageRecord(BaseModel):
    id: int
    title: str
    body: str
    source_url: Optional[str] = None
    status: WorkflowStatus
    version: int
    category: Optional[str] = None
    urgency: Optional[Urgency] = None
    owner: Optional[str] = None
    next_action: Optional[BusinessAction] = None
    reasoning: Optional[str] = None
    policy_rule_id: Optional[str] = None
    policy_reason: Optional[str] = None
    requires_approval: bool = False
    approval_policy: Optional[ApprovalPolicyKind] = None
    dry_run: Optional[DryRunAction] = None
    created_at: datetime
    updated_at: datetime
