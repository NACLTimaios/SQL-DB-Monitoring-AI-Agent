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

    def save_action(self, action: ActionQueue) -> None:
        """Persist an action queue entry."""
        self._session.add(action)
        logger.debug(
            "Queued action: domain=%s type=%s risk=%s",
            action.domain, action.action_type, action.risk_level
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

    def get_pending_actions(self, limit: int = 20) -> list[ActionQueue]:
        """Return up to *limit* pending action queue items."""
        return (
            self._session.query(ActionQueue)
            .filter(ActionQueue.status == "pending")
            .order_by(ActionQueue.created_at.desc())
            .limit(limit)
            .all()
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

    def get_incidents_timeline(
        self, hours: int = 24, severity: str = "warning"
    ) -> list[dict]:
        """Return incidents (critical/warning insights) within the past N hours.

        Groups by hour and returns count, latest severity, and sample events.
        """
        from datetime import datetime, timedelta, timezone

        now = datetime.now(tz=timezone.utc)
        cutoff = now - timedelta(hours=hours)

        # Fetch all critical/warning insights in the time window
        rows = (
            self._session.query(Insight)
            .filter(
                Insight.timestamp >= cutoff,
                Insight.severity.in_(["critical", "warning"]),
            )
            .order_by(Insight.timestamp.asc())
            .all()
        )

        # Group by hour
        buckets: dict[str, list] = {}
        for insight in rows:
            hour_key = insight.timestamp.strftime("%Y-%m-%dT%H:00:00Z")
            if hour_key not in buckets:
                buckets[hour_key] = []
            buckets[hour_key].append(
                {
                    "timestamp": insight.timestamp.isoformat(),
                    "domain": insight.domain,
                    "severity": insight.severity,
                    "title": insight.title,
                }
            )

        # Return bucketed data
        result = []
        for hour_key in sorted(buckets.keys()):
            events = buckets[hour_key]
            critical_count = sum(1 for e in events if e["severity"] == "critical")
            warning_count = sum(1 for e in events if e["severity"] == "warning")
            result.append(
                {
                    "hour": hour_key,
                    "critical_count": critical_count,
                    "warning_count": warning_count,
                    "total_count": len(events),
                    "sample_events": events[:3],  # First 3 events in this hour
                }
            )

        return result
