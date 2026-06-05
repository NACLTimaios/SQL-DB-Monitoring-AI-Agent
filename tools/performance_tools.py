"""Performance tools: real slow-query analyser and table size advisor."""

from tools import Tool

_LARGE_TABLE_THRESHOLD_MB = 1024.0  # 1 GB


class QueryAnalyzer(Tool):
    """Analyses slow query data from pg_stat_statements and identifies bottlenecks.

    capability_tags: [query_profiling]
    """

    capability_tags = ["query_profiling"]
    timeout_seconds = 5
    depends_on: list[str] = []

    def run(self, input_data: dict) -> dict:
        """Analyse slow queries and table sizes, returning recommendations.

        Parameters
        ----------
        input_data:
            slow_queries: list of {query, mean_time_ms, calls,
                                    total_time_ms, rows}
            table_sizes:  list of {schemaname, tablename, size_bytes, size_mb}

        Returns
        -------
        dict:
            status:            "warning" | "healthy"
            slow_query_count:  int
            top_slow_queries:  list of top-5 queries with metadata
            recommendations:   list of {query, mean_time_ms, calls, suggestion}
            action_required:   bool
        """
        slow_queries: list[dict] = input_data.get("slow_queries", [])
        table_sizes: list[dict] = input_data.get("table_sizes", [])

        # Sort by total execution time descending (already sorted from adapter,
        # but be defensive).
        sorted_queries = sorted(
            slow_queries,
            key=lambda q: q.get("total_time_ms", 0.0),
            reverse=True,
        )

        top_slow = sorted_queries[:5]

        recommendations: list[dict] = []
        for q in sorted_queries[:3]:
            suggestion = _suggest(q)
            recommendations.append(
                {
                    "query": q.get("query", "")[:120],
                    "mean_time_ms": q.get("mean_time_ms", 0.0),
                    "calls": q.get("calls", 0),
                    "suggestion": suggestion,
                }
            )

        # Largest table advice
        if table_sizes:
            largest = table_sizes[0]
            if largest["size_mb"] >= _LARGE_TABLE_THRESHOLD_MB:
                recommendations.append(
                    {
                        "query": f"table: {largest['schemaname']}.{largest['tablename']}",
                        "mean_time_ms": None,
                        "calls": None,
                        "suggestion": (
                            f"Table {largest['tablename']} is "
                            f"{largest['size_mb']:.0f} MB. "
                            "Consider range partitioning by date or archiving old rows."
                        ),
                    }
                )

        slow_count = len(slow_queries)
        status = "warning" if slow_count > 5 else "healthy"
        action_required = slow_count > 5

        return {
            "status": status,
            "slow_query_count": slow_count,
            "top_slow_queries": top_slow,
            "recommendations": recommendations,
            "action_required": action_required,
        }


def _suggest(q: dict) -> str:
    """Return a concise indexing or rewrite suggestion for a slow query."""
    query_text = q.get("query", "").lower()
    mean_ms = q.get("mean_time_ms", 0.0)
    calls = q.get("calls", 0)

    if "seq scan" in query_text or ("where" in query_text and mean_ms > 200):
        return (
            "Likely sequential scan. Add a targeted index on the filtered column(s). "
            "Run EXPLAIN (ANALYZE, BUFFERS) to confirm."
        )
    if calls > 1000 and mean_ms > 50:
        return (
            f"High-frequency query ({calls} calls, {mean_ms}ms avg). "
            "Ensure covering index exists; consider result caching if data is stable."
        )
    if "join" in query_text and mean_ms > 500:
        return (
            "Expensive JOIN detected. Verify join columns are indexed on both sides "
            "and statistics are up-to-date (ANALYZE)."
        )
    return (
        f"Mean latency {mean_ms}ms with {calls} calls. "
        "Profile with EXPLAIN ANALYZE to identify the bottleneck."
    )


class CostAdvisor(Tool):
    """Estimates cost and maintenance overhead of query optimisations (stub).

    capability_tags: [cost_analysis]
    """

    capability_tags = ["cost_analysis"]
    timeout_seconds = 2
    depends_on = ["query_analyzer"]

    def run(self, input_data: dict) -> dict:
        """Return a stub cost estimate.

        Parameters
        ----------
        input_data:
            recommendations: list of dicts from QueryAnalyzer

        Returns
        -------
        dict:
            cost_impact: str
            maintenance_overhead: str
        """
        recs = input_data.get("recommendations", [])
        count = len(recs)
        if count == 0:
            return {
                "cost_impact": "No changes recommended; no cost impact.",
                "maintenance_overhead": "None",
            }
        return {
            "cost_impact": (
                f"{count} recommendation(s) identified. "
                "Index builds are low-cost on this dataset size."
            ),
            "maintenance_overhead": (
                f"Estimated {count * 2}% additional write overhead per new index."
            ),
        }
