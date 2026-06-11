"""Capacity domain: monitors PostgreSQL disk usage, connections, and cache ratios."""

import logging
from typing import Any

from orchestrator.domains import Domain
from orchestrator.postgres_adapter import PostgreSQLAdapter
from tools.capacity_tools import CapacityForecaster

logger = logging.getLogger(__name__)

_TREND_GB_PER_DAY = 0.1  # conservative default growth assumption


class CapacityDomain(Domain):
    """Monitors database capacity using live metrics from PostgreSQL.

    interval_seconds = 60 — runs every minute.
    """

    name = "capacity"
    interval_seconds = 60
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
        self._forecaster = CapacityForecaster()

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self) -> dict:
        """Collect live capacity metrics from PostgreSQL.

        Queries pg_database_size, pg_stat_activity, and pg_statio_user_tables.

        Returns
        -------
        dict:
            disk_size_gb, connections_active, connections_max,
            connections_percent, heap_hit_ratio, index_hit_ratio
        """
        disk = self._adapter.get_disk_usage()
        conns = self._adapter.get_connections()
        cache = self._adapter.get_cache_hit_ratio()

        return {
            "disk_size_gb": disk["size_gb"],
            "connections_active": conns["active"],
            "connections_max": conns["max_connections"],
            "connections_percent": conns["percent"],
            "heap_hit_ratio": cache["heap_hit_ratio"],
            "index_hit_ratio": cache["index_hit_ratio"],
        }

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self) -> dict:
        """Run capacity analysis and return structured insight dict.

        Calls CapacityForecaster to project disk exhaustion.

        Returns
        -------
        dict:
            domain, observations, forecast, status
        """
        try:
            obs = self.observe()
        except Exception as exc:
            logger.error("Capacity observe() failed: %s", exc)
            obs = {
                "disk_size_gb": 0.0,
                "connections_active": 0,
                "connections_max": 100,
                "connections_percent": 0.0,
                "heap_hit_ratio": 0.0,
                "index_hit_ratio": 0.0,
            }

        forecast = self._forecaster.run(
            {
                "disk_size_gb": obs["disk_size_gb"],
                "trend_gb_per_day": _TREND_GB_PER_DAY,
                "connections_percent": obs["connections_percent"],
            }
        )

        status = "warning" if obs["connections_percent"] > 80 else "ok"
        if forecast.get("action_required"):
            status = "warning"

        return {
            "domain": "capacity",
            "observations": obs,
            "forecast": forecast,
            "status": status,
        }
