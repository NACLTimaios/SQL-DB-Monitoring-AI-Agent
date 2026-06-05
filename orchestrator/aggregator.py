"""Aggregates per-domain insights into a unified top-level result."""

from datetime import datetime, timezone
from typing import Any

# Severity ordering used when determining overall status.
_SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1, "ok": 0}

# Domain priority when merging — higher = more important for status roll-up.
_DOMAIN_PRIORITY = {"locks": 3, "performance": 2, "capacity": 1}


def aggregate_insights(domains_results: dict[str, Any]) -> dict:
    """Merge per-domain insight dicts into a single top-level structure.

    Parameters
    ----------
    domains_results:
        ``{domain_name: insight_dict}`` where each value is the dict
        returned by a domain's ``analyze()`` call.

    Returns
    -------
    dict with shape::

        {
            "timestamp": "<ISO-8601>",
            "domains": {domain_name: {...insights...}},
            "alerts":  [...high-priority findings...],
            "status":  "healthy" | "warning" | "critical"
        }
    """
    now = datetime.now(tz=timezone.utc).isoformat()

    alerts: list[dict] = []
    overall_severity = 0

    ordered = sorted(
        domains_results.items(),
        key=lambda kv: _DOMAIN_PRIORITY.get(kv[0], 0),
        reverse=True,
    )

    for domain_name, result in ordered:
        if not isinstance(result, dict):
            continue
        severity_label = result.get("severity", "ok")
        sev_rank = _SEVERITY_RANK.get(severity_label, 0)
        if sev_rank > overall_severity:
            overall_severity = sev_rank

        # Collect high-priority findings as alerts.
        if sev_rank >= _SEVERITY_RANK["warning"]:
            alerts.append(
                {
                    "domain": domain_name,
                    "severity": severity_label,
                    "summary": result.get("summary", f"{domain_name} alert"),
                    "details": result,
                }
            )

    # Map numeric severity back to status string.
    if overall_severity >= _SEVERITY_RANK["critical"]:
        status = "critical"
    elif overall_severity >= _SEVERITY_RANK["warning"]:
        status = "warning"
    else:
        status = "healthy"

    return {
        "timestamp": now,
        "domains": dict(domains_results),
        "alerts": alerts,
        "status": status,
    }
