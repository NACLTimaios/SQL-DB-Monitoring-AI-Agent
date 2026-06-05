"""PostgreSQL adapter: connects to a monitored database and extracts metrics."""

import logging
import time
from typing import Any, Optional

import psycopg2
import psycopg2.extras
import psycopg2.extensions

logger = logging.getLogger(__name__)

_RECONNECT_DELAY_SECONDS = 2
_RECONNECT_ATTEMPTS = 3


class PostgreSQLAdapter:
    """Thin wrapper around psycopg2 that provides metric-extraction helpers.

    All query methods return plain Python dicts/lists so callers have no
    psycopg2 dependency.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        connect_timeout: int = 5,
    ) -> None:
        """Establish a synchronous connection to PostgreSQL.

        Parameters
        ----------
        host:        Hostname or IP of the PostgreSQL server.
        port:        TCP port (typically 5432).
        database:    Database name to connect to.
        user:        Login role.
        password:    Login password.
        connect_timeout: Seconds before giving up on the initial connect.
        """
        self._dsn = {
            "host": host,
            "port": port,
            "dbname": database,
            "user": user,
            "password": password,
            "connect_timeout": connect_timeout,
        }
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._connect()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Open a new psycopg2 connection."""
        try:
            self._conn = psycopg2.connect(**self._dsn)
            self._conn.set_session(autocommit=True)
            logger.info(
                "Connected to PostgreSQL at %s:%s/%s",
                self._dsn["host"],
                self._dsn["port"],
                self._dsn["dbname"],
            )
        except psycopg2.OperationalError as exc:
            logger.error("Failed to connect to PostgreSQL: %s", exc)
            self._conn = None

    def _ensure_connected(self) -> bool:
        """Return True if the connection is alive, attempting reconnect if not."""
        if self._conn is None or self._conn.closed:
            for attempt in range(1, _RECONNECT_ATTEMPTS + 1):
                logger.warning("Reconnect attempt %d/%d …", attempt, _RECONNECT_ATTEMPTS)
                self._connect()
                if self._conn and not self._conn.closed:
                    return True
                time.sleep(_RECONNECT_DELAY_SECONDS)
            return False
        return True

    def is_healthy(self) -> bool:
        """Test connectivity with a trivial query.

        Returns
        -------
        bool:
            True if the server responds to SELECT 1.
        """
        try:
            result = self.execute("SELECT 1 AS alive")
            return bool(result)
        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def execute(self, query: str, params: Optional[tuple] = None) -> list[dict]:
        """Run a SQL query and return all rows as a list of dicts.

        Parameters
        ----------
        query:  SQL string; use %s placeholders for params.
        params: Optional tuple of bind values.

        Returns
        -------
        list of dicts, one per row.  Empty list on no rows or error.
        """
        if not self._ensure_connected():
            logger.error("Cannot execute query — no database connection.")
            return []

        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except psycopg2.Error as exc:
            logger.error("Query failed: %s\nSQL: %s", exc, query[:200])
            # Force reconnect on next call if connection is broken.
            if self._conn and self._conn.closed:
                self._conn = None
            return []

    # ------------------------------------------------------------------
    # Metric helpers
    # ------------------------------------------------------------------

    def get_disk_usage(self) -> dict:
        """Return the current database size in GB.

        Queries pg_database_size() for the connected database.

        Returns
        -------
        dict:
            db_name: str
            size_gb: float
        """
        sql = """
            SELECT
                current_database()                              AS db_name,
                pg_database_size(current_database())            AS size_bytes,
                ROUND(
                    pg_database_size(current_database())::numeric / (1024*1024*1024),
                    4
                )                                               AS size_gb
        """
        rows = self.execute(sql)
        if rows:
            row = rows[0]
            return {
                "db_name": row["db_name"],
                "size_gb": float(row["size_gb"]),
                "size_bytes": int(row["size_bytes"]),
            }
        return {"db_name": self._dsn["dbname"], "size_gb": 0.0, "size_bytes": 0}

    def get_connections(self) -> dict:
        """Return active connection count and the server maximum.

        Queries pg_stat_activity and pg_settings.

        Returns
        -------
        dict:
            active: int
            max_connections: int
            percent: float
        """
        sql = """
            SELECT
                COUNT(*)                                                    AS active,
                (SELECT setting::int FROM pg_settings WHERE name = 'max_connections')
                                                                            AS max_connections
            FROM pg_stat_activity
            WHERE state IS NOT NULL
        """
        rows = self.execute(sql)
        if rows:
            row = rows[0]
            active = int(row["active"])
            max_conn = int(row["max_connections"])
            percent = round((active / max_conn * 100) if max_conn else 0.0, 1)
            return {"active": active, "max_connections": max_conn, "percent": percent}
        return {"active": 0, "max_connections": 100, "percent": 0.0}

    def get_slow_queries(self, threshold_ms: float = 1000.0) -> list[dict]:
        """Return queries whose mean execution time exceeds *threshold_ms*.

        Requires pg_stat_statements extension.

        Parameters
        ----------
        threshold_ms: Queries faster than this (milliseconds) are excluded.

        Returns
        -------
        list of dicts:
            query, mean_time_ms, calls, total_time_ms, rows
        """
        sql = """
            SELECT
                query,
                ROUND(mean_exec_time::numeric, 2)       AS mean_time_ms,
                calls,
                ROUND(total_exec_time::numeric, 2)      AS total_time_ms,
                rows
            FROM pg_stat_statements
            WHERE mean_exec_time >= %s
            ORDER BY total_exec_time DESC
            LIMIT 50
        """
        rows = self.execute(sql, (threshold_ms,))
        return [
            {
                "query": r["query"],
                "mean_time_ms": float(r["mean_time_ms"]),
                "calls": int(r["calls"]),
                "total_time_ms": float(r["total_time_ms"]),
                "rows": int(r["rows"]),
            }
            for r in rows
        ]

    def get_locks(self) -> list[dict]:
        """Return sessions that are currently waiting on a lock.

        Queries pg_stat_activity for rows with wait_event_type in
        ('Lock', 'LWLock').

        Returns
        -------
        list of dicts:
            pid, usename, state, wait_event_type, wait_event,
            wait_seconds, query
        """
        sql = """
            SELECT
                pid,
                usename,
                state,
                wait_event_type,
                wait_event,
                ROUND(
                    EXTRACT(EPOCH FROM (now() - query_start))::numeric,
                    1
                )                                   AS wait_seconds,
                LEFT(query, 200)                    AS query
            FROM pg_stat_activity
            WHERE wait_event_type IN ('Lock', 'LWLock')
              AND state != 'idle'
            ORDER BY wait_seconds DESC NULLS LAST
        """
        rows = self.execute(sql)
        return [
            {
                "pid": r["pid"],
                "usename": r.get("usename") or "unknown",
                "state": r.get("state") or "",
                "wait_event_type": r.get("wait_event_type") or "",
                "wait_event": r.get("wait_event") or "",
                "wait_seconds": float(r["wait_seconds"]) if r["wait_seconds"] is not None else 0.0,
                "query": r.get("query") or "",
            }
            for r in rows
        ]

    def get_locks_blocking(self) -> list[dict]:
        """Return blocker → blocked chains from pg_locks.

        Joins pg_locks with pg_stat_activity twice (once for the blocker,
        once for the blocked session) to build a complete picture.

        Returns
        -------
        list of dicts:
            blocker_pid, blocker_user, blocker_query,
            blocked_pid, blocked_user, blocked_query,
            lock_type, relation
        """
        sql = """
            SELECT
                blocker.pid                             AS blocker_pid,
                blocker.usename                         AS blocker_user,
                LEFT(blocker.query, 200)                AS blocker_query,
                blocked.pid                             AS blocked_pid,
                blocked.usename                         AS blocked_user,
                LEFT(blocked.query, 200)                AS blocked_query,
                bl.locktype                             AS lock_type,
                COALESCE(bl.relation::regclass::text, '') AS relation
            FROM pg_locks bl
            JOIN pg_locks            gl      ON  gl.transactionid = bl.transactionid
                                             AND gl.pid           != bl.pid
                                             AND gl.granted        = true
            JOIN pg_stat_activity    blocked ON  blocked.pid       = bl.pid
            JOIN pg_stat_activity    blocker ON  blocker.pid       = gl.pid
            WHERE bl.granted = false
        """
        rows = self.execute(sql)
        return [
            {
                "blocker_pid": r["blocker_pid"],
                "blocker_user": r.get("blocker_user") or "unknown",
                "blocker_query": r.get("blocker_query") or "",
                "blocked_pid": r["blocked_pid"],
                "blocked_user": r.get("blocked_user") or "unknown",
                "blocked_query": r.get("blocked_query") or "",
                "lock_type": r.get("lock_type") or "",
                "relation": r.get("relation") or "",
            }
            for r in rows
        ]

    def get_cache_hit_ratio(self) -> dict:
        """Return buffer-cache hit ratios for heap and index reads.

        Queries pg_statio_user_tables and aggregates across all user tables.

        Returns
        -------
        dict:
            heap_hit_ratio: float  (0–1)
            index_hit_ratio: float (0–1)
            heap_read: int
            heap_hit: int
            index_read: int
            index_hit: int
        """
        sql = """
            SELECT
                SUM(heap_blks_read)     AS heap_read,
                SUM(heap_blks_hit)      AS heap_hit,
                SUM(idx_blks_read)      AS idx_read,
                SUM(idx_blks_hit)       AS idx_hit
            FROM pg_statio_user_tables
        """
        rows = self.execute(sql)
        if not rows:
            return {
                "heap_hit_ratio": 0.0,
                "index_hit_ratio": 0.0,
                "heap_read": 0,
                "heap_hit": 0,
                "index_read": 0,
                "index_hit": 0,
            }
        r = rows[0]
        heap_read = int(r["heap_read"] or 0)
        heap_hit = int(r["heap_hit"] or 0)
        idx_read = int(r["idx_read"] or 0)
        idx_hit = int(r["idx_hit"] or 0)

        heap_ratio = (
            round(heap_hit / (heap_hit + heap_read), 4)
            if (heap_hit + heap_read) > 0
            else 0.0
        )
        idx_ratio = (
            round(idx_hit / (idx_hit + idx_read), 4)
            if (idx_hit + idx_read) > 0
            else 0.0
        )
        return {
            "heap_hit_ratio": heap_ratio,
            "index_hit_ratio": idx_ratio,
            "heap_read": heap_read,
            "heap_hit": heap_hit,
            "index_read": idx_read,
            "index_hit": idx_hit,
        }

    def get_table_sizes(self, top_n: int = 10) -> list[dict]:
        """Return the *top_n* largest user tables by total disk size.

        Queries pg_tables joined with pg_total_relation_size().

        Parameters
        ----------
        top_n: How many tables to return (default 10).

        Returns
        -------
        list of dicts:
            schemaname, tablename, size_bytes, size_mb
        """
        sql = """
            SELECT
                schemaname,
                tablename,
                pg_total_relation_size(schemaname || '.' || tablename)          AS size_bytes,
                ROUND(
                    pg_total_relation_size(schemaname || '.' || tablename)
                    ::numeric / (1024 * 1024),
                    2
                )                                                                AS size_mb
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY size_bytes DESC
            LIMIT %s
        """
        rows = self.execute(sql, (top_n,))
        return [
            {
                "schemaname": r["schemaname"],
                "tablename": r["tablename"],
                "size_bytes": int(r["size_bytes"]),
                "size_mb": float(r["size_mb"]),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("PostgreSQL connection closed.")
