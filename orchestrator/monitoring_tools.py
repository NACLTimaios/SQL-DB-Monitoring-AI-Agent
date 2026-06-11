"""Advanced monitoring and analysis tools for database diagnostics and remediation."""

import json
import logging

logger = logging.getLogger(__name__)


def analyze_slow_queries(db_config: dict, params: dict) -> str:
    """Analyze slow queries with recommendations and impact assessment.

    Returns detailed analysis including:
    - Query performance metrics
    - Root cause diagnosis (sequential scans, missing indexes, etc.)
    - Remediation recommendations
    - Estimated impact of fixes
    """
    threshold_ms = int(params.get("threshold_ms", 100))
    limit = int(params.get("limit", 5))

    conn = None
    try:
        import psycopg2

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Get slow queries with analysis
        query = """
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            max_time,
            rows,
            CASE
                WHEN mean_time > 1000 THEN 'CRITICAL'
                WHEN mean_time > 500 THEN 'HIGH'
                WHEN mean_time > 100 THEN 'MEDIUM'
                ELSE 'LOW'
            END as severity
        FROM pg_stat_statements
        WHERE mean_time > %s
        ORDER BY total_time DESC
        LIMIT %s
        """

        cursor.execute(query, (threshold_ms, limit))
        rows = cursor.fetchall()

        if not rows:
            cursor.close()
            conn.close()
            return json.dumps({
                "summary": "No slow queries detected above threshold",
                "threshold_ms": threshold_ms,
                "recommendations": ["Monitor continues to check for performance issues"]
            })

        analysis_results = []

        for row in rows:
            query_text, calls, total_time, mean_time, max_time, rows_returned, severity = row

            # Analyze query for patterns
            recommendations = _diagnose_slow_query(query_text.lower(), mean_time, calls)

            analysis_results.append({
                "query": query_text[:100] + "..." if len(query_text) > 100 else query_text,
                "severity": severity,
                "metrics": {
                    "total_executions": calls,
                    "avg_time_ms": round(mean_time, 2),
                    "max_time_ms": round(max_time, 2),
                    "total_time_ms": round(total_time, 2),
                    "estimated_impact": _calculate_impact(mean_time, calls)
                },
                "diagnosis": {
                    "probable_causes": _identify_causes(query_text.lower()),
                    "remediation_steps": recommendations,
                    "priority": "HIGH" if severity in ["CRITICAL", "HIGH"] else "MEDIUM"
                }
            })

        cursor.close()
        conn.close()

        return json.dumps({
            "analysis": analysis_results,
            "summary": f"Found {len(analysis_results)} slow queries above {threshold_ms}ms threshold"
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "type": "analysis_error"
        })
    finally:
        if conn is not None:
            conn.close()


def check_missing_indexes(db_config: dict, params: dict) -> str:
    """Identify missing indexes based on sequential scans and query patterns.

    Returns:
    - Tables with high sequential scan counts
    - Recommended indexes based on access patterns
    - Estimated performance improvement
    """
    conn = None
    try:
        import psycopg2

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Check for tables with high sequential scan counts
        query = """
        SELECT
            schemaname,
            tablename,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            CASE
                WHEN seq_scan > 1000 THEN 'CRITICAL - Many sequential scans'
                WHEN seq_scan > 100 THEN 'HIGH - Consider indexing'
                ELSE 'LOW - Sequential scans acceptable'
            END as recommendation
        FROM pg_stat_user_tables
        WHERE seq_scan > 10
        ORDER BY seq_scan DESC
        LIMIT 10
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        recommendations = []

        for row in rows:
            schema, table, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch, rec = row

            # Get columns frequently used in queries
            col_query = """
            SELECT attname
            FROM pg_stat_user_columns
            WHERE relname = %s AND schemaname = %s
            ORDER BY avg_width DESC
            LIMIT 3
            """

            cursor.execute(col_query, (table, schema))
            columns = [col[0] for col in cursor.fetchall()]

            recommendations.append({
                "table": f"{schema}.{table}",
                "sequential_scans": seq_scan,
                "index_scans": idx_scan,
                "scan_ratio": round(seq_scan / (idx_scan + 1), 2),
                "recommendation": rec,
                "potential_index_columns": columns,
                "suggested_index": f"CREATE INDEX idx_{table}_{'_'.join(columns[:2])} ON {schema}.{table} ({', '.join(columns[:2])})" if columns else None,
                "expected_improvement": "Up to 50-80% query performance improvement possible" if seq_scan > 100 else "Marginal improvement"
            })

        cursor.close()
        conn.close()

        return json.dumps({
            "index_analysis": recommendations,
            "summary": f"Identified {len(recommendations)} tables with potential index improvements"
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "type": "index_analysis_error"
        })
    finally:
        if conn is not None:
            conn.close()


def check_table_bloat(db_config: dict, params: dict) -> str:
    """Analyze table bloat and recommend VACUUM/ANALYZE.

    Returns:
    - Table sizes and bloat estimates
    - Dead tuple counts
    - Last VACUUM/ANALYZE times
    - Recommendations
    """
    conn = None
    try:
        import psycopg2

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Get table bloat information
        query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            n_live_tup,
            n_dead_tup,
            ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_ratio,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY n_dead_tup DESC
        LIMIT 15
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        bloat_analysis = []

        for row in rows:
            schema, table, size, live, dead, dead_ratio, vac, avac, ana, aana = row

            action = "NORMAL"
            if dead_ratio and dead_ratio > 20:
                action = "URGENT - Run VACUUM ANALYZE"
            elif dead_ratio and dead_ratio > 10:
                action = "HIGH - Schedule VACUUM"
            elif dead_ratio and dead_ratio > 5:
                action = "MEDIUM - Consider VACUUM"

            bloat_analysis.append({
                "table": f"{schema}.{table}",
                "size": size,
                "live_tuples": live,
                "dead_tuples": dead,
                "dead_percentage": dead_ratio,
                "status": action,
                "last_maintenance": {
                    "vacuum": str(vac) if vac else "Never",
                    "autovacuum": str(avac) if avac else "Never",
                    "analyze": str(ana) if ana else "Never",
                    "autoanalyze": str(aana) if aana else "Never"
                },
                "remediation": f"VACUUM ANALYZE {schema}.{table};" if dead_ratio and dead_ratio > 5 else "Monitoring continues"
            })

        cursor.close()
        conn.close()

        return json.dumps({
            "bloat_analysis": bloat_analysis,
            "summary": f"Analyzed {len(bloat_analysis)} tables for bloat"
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "type": "bloat_analysis_error"
        })
    finally:
        if conn is not None:
            conn.close()


def get_performance_schema(db_config: dict, params: dict) -> str:
    """Access PostgreSQL performance schema for advanced diagnostics.

    Returns system catalog information about:
    - Query execution statistics
    - Index effectiveness
    - Connection information
    - Table and index statistics
    """
    query_type = params.get("query_type", "overview")

    conn = None
    try:
        import psycopg2

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        queries = {
            "overview": """
                SELECT
                    datname,
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    sum(idx_blks_read) as idx_read,
                    sum(idx_blks_hit) as idx_hit
                FROM pg_statio_user_tables
                GROUP BY datname
            """,
            "index_effectiveness": """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    CASE
                        WHEN idx_scan = 0 THEN 'UNUSED'
                        WHEN idx_tup_fetch = 0 THEN 'NOT EFFECTIVE'
                        ELSE 'ACTIVE'
                    END as status
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
            """,
            "connection_stats": """
                SELECT
                    datname,
                    count(*) as active_connections,
                    max(query_start) as last_query_time
                FROM pg_stat_activity
                GROUP BY datname
            """,
            "cache_efficiency": """
                SELECT
                    sum(heap_blks_hit) as cache_hits,
                    sum(heap_blks_read) as disk_reads,
                    ROUND(100 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2) as hit_ratio
                FROM pg_statio_user_tables
            """
        }

        query = queries.get(query_type, queries["overview"])
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        results = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()

        return json.dumps({
            "query_type": query_type,
            "results": results,
            "count": len(results)
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "type": "schema_query_error"
        })
    finally:
        if conn is not None:
            conn.close()


def execute_remediation(db_config: dict, params: dict, guardrails: dict) -> str:
    """Execute database remediation commands with proper guardrails.

    Supported operations:
    - VACUUM (cleanup dead tuples)
    - ANALYZE (update statistics)
    - REINDEX (rebuild indexes)
    - CREATE INDEX (with approval)
    """
    action = params.get("action", "").upper()
    table = params.get("table", "")
    index_name = params.get("index_name", "")
    columns = params.get("columns", [])

    # Check guardrails
    if not guardrails.get("allow_remediation", False):
        return json.dumps({
            "error": "Remediation actions are not enabled",
            "hint": "Administrator must enable remediation in guardrails"
        })

    allowed_actions = ["VACUUM", "ANALYZE", "VACUUM_ANALYZE", "REINDEX"]
    if action not in allowed_actions:
        return json.dumps({
            "error": f"Action '{action}' not allowed",
            "allowed_actions": allowed_actions
        })

    # Validate table name to prevent SQL identifier injection.
    # Table/index identifiers cannot be passed as bound parameters, so they
    # must be safely quoted via psycopg2.sql.Identifier and validated.
    if not table:
        return json.dumps({"error": "No table specified", "action": action})

    conn = None
    cursor = None
    try:
        import psycopg2
        from psycopg2 import sql

        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Build command with safely-quoted identifier (prevents injection)
        ident = sql.Identifier(table)
        if action == "VACUUM":
            cmd = sql.SQL("VACUUM (ANALYZE FALSE, VERBOSE) {}").format(ident)
        elif action == "ANALYZE":
            cmd = sql.SQL("ANALYZE {}").format(ident)
        elif action == "VACUUM_ANALYZE":
            cmd = sql.SQL("VACUUM ANALYZE {}").format(ident)
        elif action == "REINDEX":
            cmd = sql.SQL("REINDEX TABLE {}").format(ident)

        # VACUUM cannot run inside a transaction block
        conn.autocommit = True
        cursor.execute(cmd)

        return json.dumps({
            "success": True,
            "action": action,
            "target": table,
            "message": f"{action} completed successfully on {table}",
            "next_steps": "Monitor query performance to verify improvements"
        })

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "action": action,
            "type": "remediation_error"
        })
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# Helper functions

def _diagnose_slow_query(query_text: str, mean_time: float, calls: int) -> list:
    """Generate recommendations based on query pattern analysis."""
    recommendations = []

    if "select" in query_text and "join" in query_text:
        recommendations.append("Complex JOIN detected - verify all join conditions are indexed")

    if "select *" in query_text:
        recommendations.append("SELECT * found - specify only needed columns to reduce I/O")

    if "where" not in query_text:
        recommendations.append("No WHERE clause found - query scans entire table, add filtering")

    if calls > 100 and mean_time > 100:
        impact = calls * mean_time / 1000
        recommendations.append(f"High-frequency query ({calls} calls) - optimization would save ~{impact:.0f}s per execution cycle")

    if mean_time > 1000:
        recommendations.append("Query exceeds 1 second - consider adding indexes or query restructuring")

    if not recommendations:
        recommendations.append("Review execution plan with EXPLAIN ANALYZE")

    return recommendations


def _identify_causes(query_text: str) -> list:
    """Identify probable causes of slow query performance."""
    causes = []

    if "join" in query_text:
        causes.append("Missing indexes on JOIN columns")

    if "select *" in query_text:
        causes.append("Unnecessary columns being fetched")

    if "like" in query_text or "ilike" in query_text:
        causes.append("Full text scan due to LIKE pattern")

    if "where" not in query_text:
        causes.append("Table scan without filtering")

    if "order by" in query_text:
        causes.append("Sorting operation without indexed columns")

    if "group by" in query_text:
        causes.append("Grouping operation may require sort")

    if not causes:
        causes.append("Inefficient query structure or suboptimal execution plan")

    return causes


def _calculate_impact(mean_time: float, calls: int) -> str:
    """Calculate business impact of slow query."""
    total_time = (mean_time * calls) / 1000  # Convert to seconds

    if total_time > 3600:
        return f"CRITICAL: {total_time/3600:.1f} hours wasted per execution cycle"
    elif total_time > 60:
        return f"HIGH: {total_time/60:.1f} minutes wasted per execution cycle"
    elif total_time > 5:
        return f"MEDIUM: {total_time:.1f} seconds wasted per execution cycle"
    else:
        return "LOW: Optimization would provide minimal impact"
