"""Repository: thin data-access layer over the ORM models."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from store.models import ActionQueue, Analysis, Insight, Observation

logger = logging.getLogger(__name__)


class Repository:
    """Provides all persistence operations for the monitoring agent.

    All writes are append-only; rows are never updated or deleted by this
    class.  Callers are responsible for session lifecycle (commit/rollback).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def save_observation(self, obs: Observation) -> None:
        """Persist a raw metric observation."""
        self._session.add(obs)
        logger.debug("Queued observation: domain=%s metric=%s", obs.domain, obs.metric_name)

    def save_analysis(self, analysis: Analysis) -> None:
        """Persist a domain analysis record."""
        self._session.add(analysis)
        logger.debug("Queued analysis: domain=%s", analysis.domain)

    def save_insight(self, insight: Insight) -> None:
        """Persist an insight."""
        self._session.add(insight)
        logger.debug(
            "Queued insight: domain=%s severity=%s", insight.domain, insight.severity
        )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_latest_analysis(self, domain: str, limit: int = 1) -> list[Analysis]:
        """Return the most recent *limit* analyses for *domain*."""
        return (
            self._session.query(Analysis)
            .filter(Analysis.domain == domain)
            .order_by(Analysis.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_insights_pending(
        self, status: str = "pending", limit: int = 10
    ) -> list[Insight]:
        """Return up to *limit* insights with the given *status*."""
        return (
            self._session.query(Insight)
            .filter(Insight.status == status)
            .order_by(Insight.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_insights_by_domain(
        self, domain: str, status: str = "pending", limit: int = 10
    ) -> list[Insight]:
        return (
            self._session.query(Insight)
            .filter(Insight.domain == domain, Insight.status == status)
            .order_by(Insight.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_activity_feed(self, limit: int = 30) -> list[dict]:
        """Return a chronological mixed feed of Observations, Analyses, Insights.

        Each entry is a dict with ``type``, ``timestamp``, and the row's
        relevant fields so the API layer doesn't need to know the ORM.
        """
        feed: list[dict] = []

        obs_rows = (
            self._session.query(Observation)
            .order_by(Observation.timestamp.desc())
            .limit(limit)
            .all()
        )
        for o in obs_rows:
            feed.append(
                {
                    "type": "observation",
                    "timestamp": o.timestamp.isoformat() if o.timestamp else None,
                    "domain": o.domain,
                    "metric_name": o.metric_name,
                    "value": o.value,
                }
            )

        analysis_rows = (
            self._session.query(Analysis)
            .order_by(Analysis.timestamp.desc())
            .limit(limit)
            .all()
        )
        for a in analysis_rows:
            feed.append(
                {
                    "type": "analysis",
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "domain": a.domain,
                    "confidence": a.confidence,
                    "findings": a.findings,
                }
            )

        insight_rows = (
            self._session.query(Insight)
            .order_by(Insight.timestamp.desc())
            .limit(limit)
            .all()
        )
        for i in insight_rows:
            feed.append(
                {
                    "type": "insight",
                    "timestamp": i.timestamp.isoformat() if i.timestamp else None,
                    "domain": i.domain,
                    "title": i.title,
                    "severity": i.severity,
                    "status": i.status,
                }
            )

        feed.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        return feed[:limit]

    def count_pending_approvals(self) -> int:
        """Return the number of action-queue items awaiting approval."""
        return (
            self._session.query(ActionQueue)
            .filter(ActionQueue.status == "pending")
            .count()
        )

    def get_action(self, action_id: str) -> ActionQueue | None:
        return self._session.query(ActionQueue).filter(ActionQueue.id == action_id).first()

    def update_action_status(
        self, action_id: str, status: str, notes: str | None = None
    ) -> bool:
        """Set the status of an ActionQueue entry; return True if found."""
        action = self.get_action(action_id)
        if action is None:
            return False
        action.status = status
        if notes:
            action.decision_notes = notes
        logger.info("Action %s status → %s", action_id, status)
        return True
