"""Locks domain: monitors PostgreSQL lock contention at high frequency."""

import logging

from orchestrator.domains import Domain
from orchestrator.postgres_adapter import PostgreSQLAdapter
from tools.locks_tools import LockAnalyzer

logger = logging.getLogger(__name__)


class LocksDomain(Domain):
    """Detects lock waits and blocking chains in PostgreSQL.

    interval_seconds = 10 — runs every 10 seconds.
    """

    name = "locks"
    interval_seconds = 10
    enabled = True

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        db = config.get("monitored_db", {})
        self._adapter = PostgreSQLAdapter(
            host=db.get("host", "10.0.1.189"),
            port=int(db.get("port", 5432)),
            database=db.get("database", "shopdb"),
            user=db.get("user", "monitoring"),
            password=db.get("password", "changeme"),
        )
        self._analyzer = LockAnalyzer()

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self) -> dict:
        """Collect live lock state from PostgreSQL.

        Queries pg_stat_activity for waiting sessions and pg_locks for
        blocker/blocked chains.

        Returns
        -------
        dict:
            waiting_sessions: list of {pid, usename, wait_event_type,
                                        wait_event, wait_seconds, query}
            blocking_chains:  list of {blocker_pid, blocker_user,
                                        blocker_query, blocked_pid,
                                        blocked_user, blocked_query,
                                        lock_type, relation}
        """
        waiting_sessions = self._adapter.get_locks()
        blocking_chains = self._adapter.get_locks_blocking()
        return {
            "waiting_sessions": waiting_sessions,
            "blocking_chains": blocking_chains,
        }

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self) -> dict:
        """Analyse lock state and return structured insight dict.

        Returns
        -------
        dict:
            domain, observations, analysis, status
        """
        try:
            obs = self.observe()
        except Exception as exc:
            logger.error("Locks observe() failed: %s", exc)
            obs = {"waiting_sessions": [], "blocking_chains": []}

        analysis = self._analyzer.run(
            {
                "waiting_sessions": obs["waiting_sessions"],
                "blocking_chains": obs["blocking_chains"],
            }
        )

        status = "ok"
        if obs["blocking_chains"]:
            status = "critical"
        elif obs["waiting_sessions"]:
            status = "warning"

        return {
            "domain": "locks",
            "observations": obs,
            "analysis": analysis,
            "status": status,
        }
