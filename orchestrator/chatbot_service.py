"""Chatbot service: handles LLM interactions and tool execution."""

import json
import logging
import os
import psycopg2
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Default system prompt for the chatbot
DEFAULT_SYSTEM_PROMPT = """You are a database assistant for the 'shopdb' PostgreSQL database. You help users query and analyze data.

## Database Schema
The database contains the following tables:
- **customers**: id (PRIMARY KEY), name, email, created_at
- **products**: product_id (PRIMARY KEY), name, category, price, stock, created_at
- **orders**: order_id (PRIMARY KEY), customer_id (FOREIGN KEY), order_date, status, created_at
- **order_items**: item_id (PRIMARY KEY), order_id (FOREIGN KEY), product_id (FOREIGN KEY), quantity, price, created_at

## Supported Operations
- **SELECT queries**: Always available for data analysis and reporting
- **INSERT/UPDATE/DELETE**: Available if enabled by administrators via guardrails
- **DDL (CREATE/ALTER/DROP)**: Only available if explicitly enabled by administrators

## Guidelines for Queries
1. Always use the query_database tool to execute SQL queries
2. Interpret ambiguous queries intelligently:
   - "customers" → SELECT FROM customers table
   - "orders" → SELECT FROM orders table
   - "products" → SELECT FROM products table
   - "insert customer X with email Y" → INSERT INTO customers (name, email) VALUES (X, Y)
3. Use COUNT(*) for counting records
4. Use JOINs when the query spans multiple tables
5. Respond with business-friendly summaries, not raw JSON

## Safety Rules
- Execute queries according to configured guardrails
- The backend will enforce write operation restrictions
- If a write operation is not allowed, the backend will return an error with details
- Limit results to 1000 rows maximum
- Queries timeout after 5 seconds
- Always explain what query you're executing before running it

## Response Style
- Answer questions directly and concisely
- When executing queries, show the result in human-readable format
- Example: "There are 500 customers in the database." (not raw JSON)
- For multi-row results, summarize or show key insights
- If data is sensitive or unusual, flag it for the user"""

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
    allow_writes = guardrails.get("allow_writes", False)
    allow_ddl = guardrails.get("allow_ddl", False)

    query_upper = query.strip().upper()

    # Check for DDL operations
    if any(keyword in query_upper for keyword in ["CREATE", "ALTER", "DROP"]):
        if not allow_ddl:
            return "Error: DDL operations (CREATE, ALTER, DROP) are not allowed"

    # Check for DML write operations
    if any(keyword in query_upper for keyword in ["INSERT", "UPDATE", "DELETE"]):
        if not allow_writes:
            return "Error: Write operations (INSERT, UPDATE, DELETE) are not allowed"

    # If writes allowed, accept INSERT/UPDATE/DELETE. Otherwise require SELECT
    if not allow_writes and not query_upper.startswith("SELECT"):
        return "Error: Only SELECT queries are allowed"

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        # Remove trailing semicolon before processing
        query_clean = query.rstrip().rstrip(';')

        # Only add LIMIT if query doesn't already have one
        if 'LIMIT' not in query_clean.upper():
            query_clean = f"{query_clean} LIMIT {min(limit, guardrails.get('max_rows_return', 1000))}"

        cursor.execute(query_clean)

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

    def _clean_assistant_message(self, message: str) -> str:
        """Clean assistant message by formatting JSON results as natural language."""
        import re
        import json

        # Remove [Executed tool_name] markers
        message = re.sub(r'\[Executed [^\]]+\]\n?', '', message)

        # Extract and format all JSON objects and arrays
        def format_json(json_str: str) -> str:
            """Format JSON data as natural language."""
            try:
                data = json.loads(json_str)
            except:
                return json_str

            # Handle dictionaries with nested metrics
            if isinstance(data, dict):
                # Check for metrics response (has connections, disk_usage, cache_hit_ratio)
                if 'connections' in data and 'disk_usage' in data:
                    lines = []

                    # Format connections
                    if isinstance(data.get('connections'), dict):
                        conns = data['connections']
                        lines.append(f"Connections: {conns.get('active', 0)} active / {conns.get('max_connections', 0)} max ({conns.get('percent', 0):.1f}%)")

                    # Format disk usage
                    if isinstance(data.get('disk_usage'), dict):
                        disk = data['disk_usage']
                        lines.append(f"Disk: {disk.get('size_gb', 0):.2f} GB used")

                    # Format cache hit ratio
                    if isinstance(data.get('cache_hit_ratio'), dict):
                        cache = data['cache_hit_ratio']
                        lines.append(f"Cache Hit Ratio: Heap {cache.get('heap_hit_ratio', 0):.1%}, Index {cache.get('index_hit_ratio', 0):.1%}")

                    return " | ".join(lines)

                # Check for locks response
                if 'waiting_sessions' in data or 'blocking_chains' in data:
                    lines = []

                    waiting = data.get('waiting_sessions', [])
                    blocking = data.get('blocking_chains', [])

                    if waiting:
                        lines.append(f"{len(waiting)} waiting session(s)")
                    if blocking:
                        lines.append(f"{len(blocking)} blocking chain(s)")

                    if not lines:
                        lines.append("No locks detected")

                    return " | ".join(lines)

                # Generic nested object - format as key-value pairs
                if data:
                    pairs = []
                    for key, value in data.items():
                        if key not in ['created_at', 'updated_at']:
                            if isinstance(value, dict):
                                # For nested dicts, show count or first few items
                                if value:
                                    pairs.append(f"{key}: {len(value)} items" if isinstance(value, dict) else f"{key}: {value}")
                            elif isinstance(value, (int, float)):
                                if isinstance(value, float):
                                    pairs.append(f"{key}: {value:.2f}")
                                else:
                                    pairs.append(f"{key}: {value}")
                            elif value:
                                pairs.append(f"{key}: {value}")

                    if pairs:
                        return " | ".join(pairs)

                return json_str

            # Handle lists
            if isinstance(data, list):
                if not data:
                    return "No results found."

                # Single row with aggregate functions
                if len(data) == 1:
                    row = data[0]
                    if isinstance(row, dict):
                        if 'count' in row:
                            return f"The result is: {row['count']}."
                        elif 'avg' in row:
                            return f"The average is: {row['avg']:.2f}." if isinstance(row['avg'], float) else f"The average is: {row['avg']}."
                        elif 'sum' in row:
                            return f"The total is: {row['sum']}." if isinstance(row['sum'], (int, float)) else f"The total is: {row['sum']}."
                        elif 'max' in row:
                            return f"The maximum is: {row['max']}."
                        elif 'min' in row:
                            return f"The minimum is: {row['min']}."

                # Multiple rows - format as list
                if len(data) > 1:
                    summary_lines = []
                    for i, row in enumerate(data, 1):
                        if isinstance(row, dict):
                            # Format each row nicely
                            parts = []
                            for key, value in row.items():
                                if key not in ['created_at', 'updated_at', 'id']:
                                    if isinstance(value, float):
                                        parts.append(f"{key}: {value:.2f}")
                                    else:
                                        parts.append(f"{key}: {value}")
                            if parts:
                                summary_lines.append(f"{i}. " + " | ".join(parts))
                        else:
                            summary_lines.append(f"{i}. {row}")

                    if summary_lines:
                        return "\n" + "\n".join(summary_lines)

                return json_str

            return json_str

        # Pattern to match JSON objects and arrays at various nesting levels
        # This tries to find balanced braces and brackets
        def find_json_blocks(text):
            """Find all JSON blocks (objects and arrays) in text."""
            blocks = []
            depth = 0
            start = -1
            in_string = False
            escape_next = False

            for i, char in enumerate(text):
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char in '{[':
                    if depth == 0:
                        start = i
                    depth += 1
                elif char in '}]':
                    depth -= 1
                    if depth == 0 and start != -1:
                        blocks.append((start, i + 1))
                        start = -1

            return blocks

        # Find and replace all JSON blocks
        json_blocks = find_json_blocks(message)
        for start, end in reversed(json_blocks):  # Reverse to maintain indices
            json_text = message[start:end]
            formatted = format_json(json_text)
            message = message[:start] + formatted + message[end:]

        # Clean up multiple newlines
        message = re.sub(r'\n\n+', '\n', message)

        return message.strip()

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

            # Clean the message to remove tool execution details
            cleaned_message = self._clean_assistant_message(response.assistant_message)

            return {
                "assistant_message": cleaned_message,
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
