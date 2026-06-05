"""HITL generator: creates human-in-the-loop action queue items based on monitoring data."""

import logging
import random
from datetime import datetime, timezone

from store.models import ActionQueue
from store.repository import Repository

logger = logging.getLogger(__name__)


class HITLGenerator:
    """Generates HITL actions based on domain analysis results."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def generate_actions_from_insights(self, domain_results: dict) -> list[ActionQueue]:
        """Analyze domain results and generate HITL actions if needed."""
        actions: list[ActionQueue] = []

        # Capacity domain: check for disk growth or connection issues
        capacity_result = domain_results.get("capacity", {})
        if capacity_result and "error" not in capacity_result:
            actions.extend(self._check_capacity(capacity_result))

        # Performance domain: check for slow queries
        perf_result = domain_results.get("performance", {})
        if perf_result and "error" not in perf_result:
            actions.extend(self._check_performance(perf_result))

        # Locks domain: check for severe contention
        locks_result = domain_results.get("locks", {})
        if locks_result and "error" not in locks_result:
            actions.extend(self._check_locks(locks_result))

        return actions

    def _check_capacity(self, result: dict) -> list[ActionQueue]:
        """Generate HITL actions for capacity issues."""
        actions: list[ActionQueue] = []
        analysis = result.get("analysis", {})
        obs = result.get("observations", {})
        forecast = result.get("forecast", {})

        # Action: Index bloat analysis if cache hit ratio is poor
        heap_hit = obs.get("heap_hit_ratio", 1.0)
        index_hit = obs.get("index_hit_ratio", 1.0)
        if heap_hit < 0.90 or index_hit < 0.90:
            actions.append(
                ActionQueue(
                    domain="capacity",
                    action_type="analyze_index_usage",
                    risk_level="low",
                    payload={
                        "heap_hit_ratio": heap_hit,
                        "index_hit_ratio": index_hit,
                        "recommendation": f"Run ANALYZE and check index usage. Heap hit: {heap_hit*100:.1f}%, Index hit: {index_hit*100:.1f}%",
                    },
                )
            )

        # Action: Archive old data if growth trend is concerning
        days_remaining = forecast.get("days_remaining", 1000)
        if days_remaining < 180:
            actions.append(
                ActionQueue(
                    domain="capacity",
                    action_type="plan_archival",
                    risk_level="medium",
                    payload={
                        "days_remaining": days_remaining,
                        "recommendation": f"Database will be full in {days_remaining} days. Plan data archival strategy.",
                    },
                )
            )

        return actions

    def _check_performance(self, result: dict) -> list[ActionQueue]:
        """Generate HITL actions for performance issues."""
        actions: list[ActionQueue] = []
        analysis = result.get("analysis", {})
        slow_queries = analysis.get("top_slow_queries", [])

        # Action: Optimize top slow query
        if slow_queries and len(slow_queries) > 0:
            top_query = slow_queries[0]
            mean_time = top_query.get("mean_time_ms", 0)
            if mean_time > 200:  # Very slow
                actions.append(
                    ActionQueue(
                        domain="performance",
                        action_type="optimize_query",
                        risk_level="medium",
                        payload={
                            "query": top_query.get("query", "")[:100],
                            "mean_time_ms": mean_time,
                            "calls": top_query.get("calls", 1),
                            "recommendation": f"Query taking {mean_time:.0f}ms on average. Run EXPLAIN ANALYZE and consider indexing.",
                        },
                    )
                )

        # Action: Vacuum if table sizes are growing
        tables = result.get("observations", {}).get("table_sizes", [])
        if tables and len(tables) > 1:
            largest = tables[0]
            size_mb = largest.get("size_mb", 0)
            if size_mb > 50:  # Large table
                actions.append(
                    ActionQueue(
                        domain="performance",
                        action_type="maintenance_vacuum",
                        risk_level="low",
                        payload={
                            "table": largest.get("tablename", ""),
                            "size_mb": size_mb,
                            "recommendation": f"Table '{largest.get('tablename')}' is {size_mb:.1f}MB. Consider VACUUM or ANALYZE.",
                        },
                    )
                )

        return actions

    def _check_locks(self, result: dict) -> list[ActionQueue]:
        """Generate HITL actions for lock contention."""
        actions: list[ActionQueue] = []
        analysis = result.get("analysis", {})

        waiting_count = analysis.get("waiting_session_count", 0)
        chains_count = analysis.get("blocking_chains_count", 0)
        risk_level = analysis.get("risk_level", "healthy")

        # Action: Kill blocking session if critical
        if chains_count > 0 and risk_level == "critical":
            blocking_chains = result.get("observations", {}).get("blocking_chains", [])
            if blocking_chains:
                chain = blocking_chains[0]
                actions.append(
                    ActionQueue(
                        domain="locks",
                        action_type="kill_blocking_session",
                        risk_level="high",
                        payload={
                            "blocker_pid": chain.get("blocker_pid"),
                            "blocked_pid": chain.get("blocked_pid"),
                            "wait_seconds": chain.get("wait_seconds", 0),
                            "recommendation": f"Critical blocking detected. PID {chain.get('blocker_pid')} blocking PID {chain.get('blocked_pid')} for {chain.get('wait_seconds', 0):.1f}s",
                        },
                    )
                )

        # Action: Connection pool review if many waiting sessions
        if waiting_count >= 5:
            actions.append(
                ActionQueue(
                    domain="locks",
                    action_type="review_connection_pool",
                    risk_level="medium",
                    payload={
                        "waiting_sessions": waiting_count,
                        "recommendation": f"High number of waiting sessions ({waiting_count}). Review connection pool settings and application behavior.",
                    },
                )
            )

        return actions

    def generate_random_issue(self) -> ActionQueue | None:
        """Generate a random synthetic HITL issue for testing (10% chance)."""
        if random.random() > 0.10:  # Only 10% of the time
            return None

        issue_types = [
            {
                "domain": "capacity",
                "action_type": "storage_plan_review",
                "risk_level": "low",
                "payload": {
                    "recommendation": "Review storage growth trends and plan for capacity expansion.",
                },
            },
            {
                "domain": "performance",
                "action_type": "query_optimization_review",
                "risk_level": "low",
                "payload": {
                    "recommendation": "Review slowest queries and consider optimization or caching strategies.",
                },
            },
            {
                "domain": "locks",
                "action_type": "application_review",
                "risk_level": "low",
                "payload": {
                    "recommendation": "Review application transaction isolation levels and connection handling.",
                },
            },
            {
                "domain": "capacity",
                "action_type": "backup_verification",
                "risk_level": "medium",
                "payload": {
                    "recommendation": "Verify recent backups are restorable and stored securely.",
                },
            },
        ]

        issue = random.choice(issue_types)
        return ActionQueue(
            domain=issue["domain"],
            action_type=issue["action_type"],
            risk_level=issue["risk_level"],
            payload=issue["payload"],
        )
