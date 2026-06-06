"""Chatbot service: handles LLM interactions and tool execution."""

import json
import logging
import os
import psycopg2
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Default system prompt for the chatbot
DEFAULT_SYSTEM_PROMPT = """You are a helpful database monitoring assistant for a PostgreSQL database.
You can provide information about the database state, execute queries, and help with monitoring insights.

Always be clear about what data you're retrieving and explain the results in business terms.
When executing queries, explain what you're doing before executing them.
If something seems unusual or risky, ask for clarification before proceeding."""

# Available tools the chatbot can use
AVAILABLE_TOOLS = {
    "query_database": {
        "description": "Execute a SELECT query against the monitored database",
        "parameters": {
            "query": "SQL SELECT query to execute",
            "limit": "Maximum rows to return (default 100)",
        },
    },
    "get_metrics": {
        "description": "Get current database metrics (connections, disk, cache hit ratio)",
        "parameters": {},
    },
    "get_slow_queries": {
        "description": "Get list of slow queries from pg_stat_statements",
        "parameters": {
            "threshold_ms": "Query time threshold in milliseconds (default 100)",
            "limit": "Maximum queries to return (default 10)",
        },
    },
    "get_table_stats": {
        "description": "Get statistics and sizes of tables in the database",
        "parameters": {},
    },
    "check_locks": {
        "description": "Check for active locks and blocking sessions",
        "parameters": {},
    },
}

# Default guardrails
DEFAULT_GUARDRAILS = {
    "allow_writes": False,  # No INSERT/UPDATE/DELETE
    "allow_ddl": False,  # No CREATE/ALTER/DROP
    "query_timeout_seconds": 5,
    "max_rows_return": 1000,
    "restricted_tables": [],  # Tables users can't query
}


# Tool executors - shared across all LLM providers
def _execute_query_database(db_config: dict, params: dict, guardrails: dict) -> str:
    """Execute a database query safely."""
    query = params.get("query", "")
    limit = int(params.get("limit", 100))

    # Guardrails checks
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed"

    if any(
        keyword in query.upper()
        for keyword in ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
    ):
        return "Error: Writes and DDL not allowed"

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(f"{query} LIMIT {min(limit, guardrails.get('max_rows_return', 1000))}")

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        results = [dict(zip(columns, row)) for row in rows]
        return json.dumps(results, default=str, indent=2)

    except Exception as e:
        return f"Query error: {str(e)}"


def _execute_get_metrics(db_config: dict, params: dict, guardrails: dict) -> str:
    """Get current database metrics."""
    try:
        from orchestrator.postgres_adapter import PostgreSQLAdapter

        adapter = PostgreSQLAdapter(**db_config)
        conns = adapter.get_connections()
        disk = adapter.get_disk_usage()
        cache_hit = adapter.get_cache_hit_ratio()

        metrics = {
            "connections": conns,
            "disk_usage": disk,
            "cache_hit_ratio": cache_hit,
        }
        return json.dumps(metrics, indent=2)
    except Exception as e:
        return f"Metrics error: {str(e)}"


def _execute_get_slow_queries(db_config: dict, params: dict, guardrails: dict) -> str:
    """Get slow queries from pg_stat_statements."""
    threshold_ms = int(params.get("threshold_ms", 100))
    limit = int(params.get("limit", 10))

    try:
        from orchestrator.postgres_adapter import PostgreSQLAdapter

        adapter = PostgreSQLAdapter(**db_config)
        queries = adapter.get_slow_queries(threshold_ms=threshold_ms)

        return json.dumps(queries[:limit], default=str, indent=2)
    except Exception as e:
        return f"Slow queries error: {str(e)}"


def _execute_get_table_stats(db_config: dict, params: dict, guardrails: dict) -> str:
    """Get table statistics and sizes."""
    try:
        from orchestrator.postgres_adapter import PostgreSQLAdapter

        adapter = PostgreSQLAdapter(**db_config)
        tables = adapter.get_table_sizes()

        return json.dumps(tables, default=str, indent=2)
    except Exception as e:
        return f"Table stats error: {str(e)}"


def _execute_check_locks(db_config: dict, params: dict, guardrails: dict) -> str:
    """Check for locks and blocking sessions."""
    try:
        from orchestrator.postgres_adapter import PostgreSQLAdapter

        adapter = PostgreSQLAdapter(**db_config)
        waiting = adapter.get_locks()
        blocking = adapter.get_locks_blocking()

        locks_info = {
            "waiting_sessions": waiting,
            "blocking_chains": blocking,
        }
        return json.dumps(locks_info, default=str, indent=2)
    except Exception as e:
        return f"Locks check error: {str(e)}"


# Map tool names to executor functions
TOOL_EXECUTORS = {
    "query_database": _execute_query_database,
    "get_metrics": _execute_get_metrics,
    "get_slow_queries": _execute_get_slow_queries,
    "get_table_stats": _execute_get_table_stats,
    "check_locks": _execute_check_locks,
}


class ChatbotService:
    """Service to handle chatbot interactions with LLM and database."""

    def __init__(self, config: dict, db_config: dict):
        """Initialize chatbot service.

        Args:
            config: Chatbot configuration (provider, model, tools, etc.)
            db_config: Database connection config for queries
        """
        self.config = config
        self.db_config = db_config
        self.llm_provider_name = config.get("llm_provider", "anthropic")
        self.system_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        self.tools = config.get("tools", list(AVAILABLE_TOOLS.keys()))
        self.guardrails = config.get("guardrails", DEFAULT_GUARDRAILS)

    def chat(self, user_message: str) -> dict:
        """Process a user message and return assistant response.

        Args:
            user_message: User's chat message

        Returns:
            Dict with assistant_message, tools_used, and execution_details
        """
        try:
            from orchestrator.llm_providers import get_provider

            # Get the appropriate provider
            provider = get_provider(self.llm_provider_name, self.config, self.db_config)

            # Send message through provider
            response = provider.chat(user_message, AVAILABLE_TOOLS)

            return {
                "assistant_message": response.assistant_message,
                "tools_used": response.tools_used,
                "stop_reason": response.stop_reason,
                "error": response.error,
            }

        except ValueError as e:
            logger.error("Invalid LLM provider: %s", e)
            return {
                "assistant_message": "",
                "tools_used": [],
                "error": str(e),
            }
        except Exception as e:
            logger.error("Chatbot error: %s", e, exc_info=True)
            return {
                "assistant_message": "",
                "tools_used": [],
                "error": str(e),
            }
