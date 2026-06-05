"""Capacity tools: disk exhaustion forecaster and storage advisory stub."""

from datetime import datetime, timedelta, timezone

from tools import Tool

_TOTAL_DISK_GB = 200.0  # OCI Free Tier block storage estimate


class CapacityForecaster(Tool):
    """Projects disk exhaustion date from current usage and growth trend.

    capability_tags: [forecasting, trending]
    """

    capability_tags = ["forecasting", "trending"]
    timeout_seconds = 2
    depends_on: list[str] = []

    def run(self, input_data: dict) -> dict:
        """Forecast when the database disk will be full.

        Parameters
        ----------
        input_data:
            disk_size_gb:        Current database size in GB.
            trend_gb_per_day:    Estimated daily growth rate in GB.
            connections_percent: Current connection utilisation (0–100).

        Returns
        -------
        dict:
            forecast_full_date: ISO datetime string
            days_remaining:     int
            confidence:         float (0–1)
            trend_gb_per_day:   float
            current_size_gb:    float
            total_capacity_gb:  float (always 200)
            action_required:    bool  (True if days_remaining < 30)
        """
        disk_size_gb: float = float(input_data.get("disk_size_gb", 0.0))
        trend_gb_per_day: float = float(input_data.get("trend_gb_per_day", 0.1))

        free_disk_gb = max(_TOTAL_DISK_GB - disk_size_gb, 0.0)

        if trend_gb_per_day <= 0:
            days_to_full = 999
        else:
            days_to_full = int(free_disk_gb / trend_gb_per_day)

        forecast_dt = datetime.now(tz=timezone.utc) + timedelta(days=days_to_full)
        confidence = 0.7 if days_to_full > 30 else 0.9
        action_required = days_to_full < 30

        return {
            "forecast_full_date": forecast_dt.isoformat(),
            "days_remaining": days_to_full,
            "confidence": confidence,
            "trend_gb_per_day": trend_gb_per_day,
            "current_size_gb": round(disk_size_gb, 4),
            "total_capacity_gb": _TOTAL_DISK_GB,
            "action_required": action_required,
        }


class StorageAdvisor(Tool):
    """Recommends storage actions based on the capacity forecast (stub).

    capability_tags: [recommendations]
    """

    capability_tags = ["recommendations"]
    timeout_seconds = 1
    depends_on = ["capacity_forecaster"]

    def run(self, input_data: dict) -> dict:
        """Return a human-readable storage recommendation.

        Parameters
        ----------
        input_data:
            days_remaining: int — from CapacityForecaster output.

        Returns
        -------
        dict:
            recommendation: str
        """
        days: int = int(input_data.get("days_remaining") or 999)

        if days < 7:
            msg = "URGENT: Expand block storage by at least 100 GB immediately."
        elif days < 30:
            msg = "Schedule storage expansion within the next two weeks."
        else:
            msg = "Storage levels healthy; no immediate action required."

        return {"recommendation": msg}
