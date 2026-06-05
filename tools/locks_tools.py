"""Locks tools: real lock contention analyser."""

from tools import Tool

_CRITICAL_WAIT_SECONDS = 300.0


class LockAnalyzer(Tool):
    """Analyses PostgreSQL lock wait data and classifies risk.

    capability_tags: [lock_analysis]
    """

    capability_tags = ["lock_analysis"]
    timeout_seconds = 1
    depends_on: list[str] = []

    def run(self, input_data: dict) -> dict:
        """Classify lock contention and generate DBA recommendations.

        Parameters
        ----------
        input_data:
            waiting_sessions: list of {pid, usename, wait_seconds, query, …}
            blocking_chains:  list of {blocker_pid, blocked_pid,
                                        blocker_query, blocked_query, …}

        Returns
        -------
        dict:
            risk_level:              "critical" | "warning" | "healthy"
            waiting_session_count:   int
            critical_locks:          list of {pid, user, wait_seconds, query}
            blocking_chains_count:   int
            recommendations:         list of str
            action_required:         bool
        """
        waiting_sessions: list[dict] = input_data.get("waiting_sessions", [])
        blocking_chains: list[dict] = input_data.get("blocking_chains", [])

        critical_locks: list[dict] = []
        for session in waiting_sessions:
            wait = float(session.get("wait_seconds", 0.0))
            if wait > _CRITICAL_WAIT_SECONDS:
                critical_locks.append(
                    {
                        "pid": session.get("pid"),
                        "user": session.get("usename", "unknown"),
                        "wait_seconds": wait,
                        "query": session.get("query", ""),
                    }
                )

        # Determine overall risk level
        if critical_locks or blocking_chains:
            risk_level = "critical"
        elif waiting_sessions:
            risk_level = "warning"
        else:
            risk_level = "healthy"

        recommendations: list[str] = []

        if blocking_chains:
            blocker_pids = list({c["blocker_pid"] for c in blocking_chains})
            recommendations.append(
                f"Blocking chains detected. Consider terminating blocker PID(s) "
                f"{blocker_pids} via SELECT pg_terminate_backend(<pid>)."
            )

        for lock in critical_locks:
            recommendations.append(
                f"Session PID {lock['pid']} (user: {lock['user']}) has been "
                f"waiting {lock['wait_seconds']:.0f}s. "
                f"Query: {lock['query'][:80]}"
            )

        if waiting_sessions and not critical_locks and not blocking_chains:
            recommendations.append(
                "Short-lived lock waits detected. Consider setting "
                "statement_timeout or lock_timeout to limit wait duration."
            )

        if not waiting_sessions and not blocking_chains:
            recommendations.append("No lock contention detected. System is healthy.")

        return {
            "risk_level": risk_level,
            "waiting_session_count": len(waiting_sessions),
            "critical_locks": critical_locks,
            "blocking_chains_count": len(blocking_chains),
            "recommendations": recommendations,
            "action_required": risk_level == "critical",
        }
