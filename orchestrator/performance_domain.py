"""Performance domain: monitors query latency and table sizes via pg_stat_statements."""

import logging

from orchestrator.domains import Domain
from orchestrator.postgres_adapter import PostgreSQLAdapter
from tools.performance_tools import QueryAnalyzer

logger = logging.getLogger(__name__)

_SLOW_QUERY_THRESHOLD_MS = 100.0


class PerformanceDomain(Domain):
    """Monitors PostgreSQL query performance using pg_stat_statements.

    interval_seconds = 300 — runs every 5 minutes.
    """

    name = "performance"
    interval_seconds = 300
    enabled = True

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        db = config.get("monitored_db", {})
        self._adapter = PostgreSQLAdapter(
            host=db.get("host", "10.0.1.189"),
            port=int(db.get("port", 5432)),
            database=db.get("database", "shopdb"),
            user=db.get("user", "monitoring"),
            password=db.get("password", ""),
        )
        self._analyzer = QueryAnalyzer()

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self) -> dict:
        """Collect live performance metrics from PostgreSQL.

        Queries pg_stat_statements for slow queries and pg_tables for sizes.

        Returns
        -------
        dict:
            slow_queries: list of {query, mean_time_ms, calls,
                                    total_time_ms, rows}
            table_sizes:  list of {schemaname, tablename, size_bytes, size_mb}
        """
        slow_queries = self._adapter.get_slow_queries(threshold_ms=_SLOW_QUERY_THRESHOLD_MS)
        table_sizes = self._adapter.get_table_sizes(top_n=10)
        return {
            "slow_queries": slow_queries,
            "table_sizes": table_sizes,
        }

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self) -> dict:
        """Run performance analysis and return structured insight dict.

        Returns
        -------
        dict:
            domain, observations, analysis, status
        """
        try:
            obs = self.observe()
        except Exception as exc:
            logger.error("Performance observe() failed: %s", exc)
            obs = {"slow_queries": [], "table_sizes": []}

        analysis = self._analyzer.run(
            {
                "slow_queries": obs["slow_queries"],
                "table_sizes": obs["table_sizes"],
            }
        )

        status = "warning" if len(obs["slow_queries"]) > 5 else "ok"

        return {
            "domain": "performance",
            "observations": obs,
            "analysis": analysis,
            "status": status,
        }
