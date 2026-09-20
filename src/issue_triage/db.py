from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class IssueWorkflowRow(Base):
    __tablename__ = "issue_workflows"
    __table_args__ = (Index("ix_issue_workflows_source_url", "source_url", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="received")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    category: Mapped[str | None] = mapped_column(String(100))
    urgency: Mapped[str | None] = mapped_column(String(10))
    owner: Mapped[str | None] = mapped_column(String(100))
    next_action: Mapped[str | None] = mapped_column(String(50))
    reasoning: Mapped[str | None] = mapped_column(Text)
    policy_rule_id: Mapped[str | None] = mapped_column(String(50))
    policy_reason: Mapped[str | None] = mapped_column(Text)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_policy: Mapped[str | None] = mapped_column(String(50))

    dry_run_comment: Mapped[str | None] = mapped_column(Text)
    dry_run_labels: Mapped[str | None] = mapped_column(Text)
    dry_run_owner: Mapped[str | None] = mapped_column(String(100))
    dry_run_action: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    decision_logs: Mapped[list[DecisionLogRow]] = relationship(back_populates="issue")


class DecisionLogRow(Base):
    __tablename__ = "decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issue_workflows.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    issue: Mapped[IssueWorkflowRow] = relationship(back_populates="decision_logs")


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./dev.db")


def make_engine(url: str | None = None):
    resolved = url or database_url()
    connect_args = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    engine_kwargs: dict = {"connect_args": connect_args}
    if resolved.startswith("sqlite") and ":memory:" in resolved:
        engine_kwargs["poolclass"] = StaticPool
    return create_engine(resolved, **engine_kwargs)


def make_session_factory(engine=None):
    engine = engine or make_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine=None) -> None:
    engine = engine or make_engine()
    Base.metadata.create_all(engine)
    _ensure_source_url_column(engine)


def _ensure_source_url_column(engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.connect() as conn:
        columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(issue_workflows)").fetchall()
        }
        if columns and "source_url" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE issue_workflows ADD COLUMN source_url VARCHAR(500)"
            )
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_issue_workflows_source_url "
                "ON issue_workflows (source_url)"
            )
            conn.commit()
