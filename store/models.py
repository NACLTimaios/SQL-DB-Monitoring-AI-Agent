"""SQLAlchemy ORM models: Observation, Analysis, Insight, ActionQueue."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Observation — raw metric snapshot (append-only)
# ---------------------------------------------------------------------------


class Observation(Base):
    """A single raw metric reading collected by a domain."""

    __tablename__ = "observations"

    id = Column(String(36), primary_key=True, default=_uuid)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    db_id = Column(String(64), nullable=True, index=True)
    domain = Column(String(64), nullable=False, index=True)
    metric_name = Column(String(128), nullable=False)
    value = Column(Float, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return (
            f"<Observation id={self.id!r} domain={self.domain!r} "
            f"metric={self.metric_name!r} value={self.value}>"
        )


# ---------------------------------------------------------------------------
# Analysis — aggregated findings for a domain cycle (append-only)
# ---------------------------------------------------------------------------


class Analysis(Base):
    """Structured findings produced by a domain's analyze() call."""

    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=_uuid)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    domain = Column(String(64), nullable=False, index=True)
    findings = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis id={self.id!r} domain={self.domain!r} "
            f"confidence={self.confidence}>"
        )


# ---------------------------------------------------------------------------
# Insight — human-readable insight derived from analysis (append-only)
# ---------------------------------------------------------------------------


class Insight(Base):
    """A surfaced finding ready for review or action."""

    __tablename__ = "insights"

    id = Column(String(36), primary_key=True, default=_uuid)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    domain = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(32), nullable=False, default="info", index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return (
            f"<Insight id={self.id!r} domain={self.domain!r} "
            f"severity={self.severity!r} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# ActionQueue — pending human-in-the-loop decisions
# ---------------------------------------------------------------------------


class ActionQueue(Base):
    """An action queued for human approval before execution."""

    __tablename__ = "action_queue"

    id = Column(String(36), primary_key=True, default=_uuid)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    domain = Column(String(64), nullable=False, index=True)
    action_type = Column(String(128), nullable=False)
    risk_level = Column(String(32), nullable=False, default="low")
    payload = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    decision_notes = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    def __repr__(self) -> str:
        return (
            f"<ActionQueue id={self.id!r} domain={self.domain!r} "
            f"action_type={self.action_type!r} status={self.status!r}>"
        )
