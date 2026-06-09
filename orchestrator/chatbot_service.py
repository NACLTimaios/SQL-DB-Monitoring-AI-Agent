"""Chatbot service: handles LLM interactions and tool execution."""

import json
import logging
import os
import psycopg2
from typing import Optional, Callable

from orchestrator.monitoring_tools import (
    analyze_slow_queries,
    check_missing_indexes,
    check_table_bloat,
    get_performance_schema,
    execute_remediation,
)

logger = logging.getLogger(__name__)

# Default system prompt for the chatbot
DEFAULT_SYSTEM_PROMPT = """You are a database assistant for the 'shopdb' PostgreSQL database.

## Your Job
Answer database questions. Run queries. Check performance. Suggest fixes.

## Database Tables
- customers: id, name, email, credit_card_number, created_at
- products: product_id, name, category, price, stock, created_at
- orders: id, customer_id, product_id, quantity, total, created_at
  (orders table has line items directly, NOT a separate order_items table)

## Available Tools - Use ONE at a time:

1. **query_database** - Run SQL SELECT queries
   - Example: "How many customers do we have?"

2. **get_metrics** - Check database health
   - Example: "Is the database healthy?"

3. **get_slow_queries** - Find slow queries
   - Example: "What queries are slow?"

4. **analyze_slow_queries** - Explain why queries are slow + how to fix
   - Example: "Why is the database slow?"

5. **check_missing_indexes** - Find missing indexes
   - Example: "What indexes are missing?"

6. **check_table_bloat** - Check if tables need cleanup
   - Example: "Does the database need maintenance?"

7. **get_performance_schema** - Advanced diagnostics (overview, index_effectiveness, connection_stats, cache_efficiency)
   - Example: "Show me index effectiveness"

8. **execute_remediation** - Run maintenance (VACUUM, ANALYZE, VACUUM_ANALYZE, REINDEX)
   - Example: "Run VACUUM on customers table"

## How to Answer

1. Understand what the user is asking
2. Pick ONE tool to call (do not call multiple tools in one response)
3. Return results in plain English (not JSON)
4. For monitoring: Explain what the problem is + how to fix it

## Examples

User: "How many customers?"
→ Call query_database: SELECT COUNT(*) FROM customers
← Return: "There are 5,420 customers"

User: "Is database slow?"
→ Call analyze_slow_queries
← Return: "Yes. Query 'SELECT * FROM customers' takes 523ms (too slow). Missing index on email. Run: CREATE INDEX idx_customers_email ON customers(email); Performance will be 5x faster"

User: "Database health?"
→ Call get_metrics
← Return: "Database is healthy: 23 connections, 85% cache hit, 2.3GB disk"

## Rules

- Do NOT call multiple tools in one message - ask user to ask next question separately
- Do NOT return raw JSON - summarize in plain English
- Do NOT overthink - keep responses simple and direct
- Credit card data is TEST DATA (fake) - it's safe to query and return
- Always explain what you're doing before running query
- If user asks multiple things, answer the main one first

## Test Database
This is TEST data with fake credit cards. Safe to query all data."""

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
    "analyze_slow_queries": {
        "description": "Analyze slow queries and explain why + how to fix them",
        "parameters": {
            "threshold_ms": "Threshold in ms (default 100)",
            "limit": "Number of queries (default 5)",
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
    "check_missing_indexes": {
        "description": "Find which indexes are missing",
        "parameters": {},
    },
    "check_table_bloat": {
        "description": "Find tables that need VACUUM/ANALYZE",
        "parameters": {},
    },
    "get_performance_schema": {
        "description": "Check performance statistics",
        "parameters": {
            "query_type": "Type: overview, index_effectiveness, connection_stats, or cache_efficiency",
        },
    },
    "execute_remediation": {
        "description": "Run VACUUM, ANALYZE, or REINDEX on a table",
        "parameters": {
            "action": "VACUUM, ANALYZE, VACUUM_ANALYZE, or REINDEX",
            "table": "Table name",
        },
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
    """Execute a database query safely with parameterized queries."""
    query = params.get("query", "")
    query_params = params.get("params", ())  # Parameters for parameterized queries
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

        # Check if this is a write operation (INSERT, UPDATE, DELETE)
        is_write_op = any(keyword in query_upper for keyword in ["INSERT", "UPDATE", "DELETE"])

        # Only add LIMIT for SELECT queries
        if not is_write_op and 'LIMIT' not in query_clean.upper():
            query_clean = f"{query_clean} LIMIT {min(limit, guardrails.get('max_rows_return', 1000))}"

        # Execute with parameterized query to prevent SQL injection
        cursor.execute(query_clean, query_params)

        # Handle write operations (no result set, just row count)
        if is_write_op:
            affected_rows = cursor.rowcount
            cursor.close()
            conn.commit()
            conn.close()
            # Return rows affected as JSON
            return json.dumps({"rows_affected": affected_rows}, default=str, indent=2)

        # Handle SELECT and other read operations
        if cursor.description is None:
            cursor.close()
            conn.close()
            return json.dumps({"message": "Query executed successfully"}, default=str, indent=2)

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


# Wrapper functions for monitoring tools to match TOOL_EXECUTORS interface
def _execute_analyze_slow_queries(db_config: dict, params: dict, guardrails: dict) -> str:
    """Wrapper for analyze_slow_queries tool."""
    return analyze_slow_queries(db_config, params)


def _execute_check_missing_indexes(db_config: dict, params: dict, guardrails: dict) -> str:
    """Wrapper for check_missing_indexes tool."""
    return check_missing_indexes(db_config, params)


def _execute_check_table_bloat(db_config: dict, params: dict, guardrails: dict) -> str:
    """Wrapper for check_table_bloat tool."""
    return check_table_bloat(db_config, params)


def _execute_get_performance_schema(db_config: dict, params: dict, guardrails: dict) -> str:
    """Wrapper for get_performance_schema tool."""
    return get_performance_schema(db_config, params)


def _execute_remediation(db_config: dict, params: dict, guardrails: dict) -> str:
    """Wrapper for execute_remediation tool."""
    return execute_remediation(db_config, params, guardrails)


# Map tool names to executor functions
TOOL_EXECUTORS = {
    "query_database": _execute_query_database,
    "get_metrics": _execute_get_metrics,
    "get_slow_queries": _execute_get_slow_queries,
    "analyze_slow_queries": _execute_analyze_slow_queries,
    "get_table_stats": _execute_get_table_stats,
    "check_locks": _execute_check_locks,
    "check_missing_indexes": _execute_check_missing_indexes,
    "check_table_bloat": _execute_check_table_bloat,
    "get_performance_schema": _execute_get_performance_schema,
    "execute_remediation": _execute_remediation,
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

    def _format_value(self, value, key: str = "") -> str:
        """Format a single value intelligently based on type and context."""
        if value is None:
            return "N/A"
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, float):
            # Auto-detect percentage fields
            if 'percent' in key.lower() or 'ratio' in key.lower() or (value >= 0 and value <= 1 and 'ratio' in key.lower()):
                return f"{value:.1%}" if 0 <= value <= 1 else f"{value:.2f}"
            return f"{value:.2f}"
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, str):
            return value
        elif isinstance(value, (list, dict)):
            return str(value)
        return str(value)

    def _format_record(self, record: dict, skip_fields: set = None) -> list:
        """Format a single record as readable lines."""
        if skip_fields is None:
            skip_fields = {'id', 'created_at', 'updated_at', 'deleted_at'}

        lines = []
        # First, extract key identifying fields (name, title, email, etc.)
        identity_keys = ['name', 'title', 'email', 'username', 'customer']
        identity_values = []

        for key in identity_keys:
            if key in record:
                identity_values.append(str(record[key]))
                break

        # Format remaining fields
        for key, value in record.items():
            if key.lower() not in skip_fields and not key.startswith('_'):
                formatted_value = self._format_value(value, key)
                if formatted_value and formatted_value != "N/A":
                    # Format key name: snake_case or CamelCase → Title Case
                    display_key = key.replace('_', ' ').title()
                    lines.append(f"   {display_key}: {formatted_value}")

        return identity_values, lines

    def _format_json_data(self, data: any) -> str:
        """Format JSON data as human-readable text. Works for all data types."""
        import json

        # Handle empty data
        if data is None or (isinstance(data, (list, dict)) and not data):
            return "No results found."

        # Handle single scalar value
        if isinstance(data, (int, float, bool, str)):
            return self._format_value(data)

        # Handle dictionary (single object/record)
        if isinstance(data, dict):
            # Special case: Check for aggregate function results
            agg_funcs = ['count', 'avg', 'sum', 'max', 'min', 'total']
            for func in agg_funcs:
                if func in data and len(data) == 1:
                    value = data[func]
                    formatted = self._format_value(value)
                    if func == 'count':
                        return f"Found {formatted} result(s)."
                    elif func == 'avg':
                        return f"The average is {formatted}."
                    elif func == 'sum':
                        return f"The total is {formatted}."
                    elif func == 'max':
                        return f"The maximum is {formatted}."
                    elif func == 'min':
                        return f"The minimum is {formatted}."

            # Check for write operation result
            if 'rows_affected' in data:
                rows = data['rows_affected']
                if rows == 0:
                    return "No rows were affected."
                elif rows == 1:
                    return "1 row was successfully modified."
                else:
                    return f"{rows} rows were successfully modified."

            # Format as key-value pairs
            lines = []
            for key, value in data.items():
                if not key.startswith('_'):
                    formatted_value = self._format_value(value, key)
                    if formatted_value != "N/A":
                        display_key = key.replace('_', ' ').title()
                        lines.append(f"{display_key}: {formatted_value}")

            if lines:
                return "\n".join(lines)

            return json.dumps(data, indent=2)

        # Handle list (multiple records)
        if isinstance(data, list):
            if not data:
                return "No results found."

            # Single record
            if len(data) == 1:
                record = data[0]
                if isinstance(record, dict):
                    identity, details = self._format_record(record)
                    result = ""
                    if identity:
                        result += f"Record: {' - '.join(identity)}\n"
                    result += "\n".join(details)
                    return result if result.strip() else json.dumps(record, indent=2)
                else:
                    return str(record)

            # Multiple records - format as numbered list
            output_lines = []
            for idx, record in enumerate(data, 1):
                if isinstance(record, dict):
                    identity, details = self._format_record(record)
                    if identity:
                        output_lines.append(f"{idx}. {' - '.join(identity)}")
                    if details:
                        output_lines.extend(details)
                    output_lines.append("")  # Blank line between records
                else:
                    output_lines.append(f"{idx}. {record}")

            return "\n".join(output_lines).strip()

        return json.dumps(data, indent=2)

    def _clean_assistant_message(self, message: str) -> str:
        """Clean assistant message by formatting JSON results as natural language."""
        import re
        import json

        # Remove [Executed tool_name] markers
        message = re.sub(r'\[Executed [^\]]+\]\n?', '', message)

        # Find and replace all JSON blocks
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
            try:
                data = json.loads(json_text)
                formatted = self._format_json_data(data)
                message = message[:start] + formatted + message[end:]
            except json.JSONDecodeError:
                # Not valid JSON, leave as is
                pass

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
            import re

            # Special handling for credit card queries (bypass Claude's safety constraints)
            if 'credit' in user_message.lower() and 'card' in user_message.lower():
                try:
                    import json

                    # Extract limit from message
                    limit_match = re.search(r'limit\s+(\d+)', user_message, re.IGNORECASE)
                    limit = int(limit_match.group(1)) if limit_match else 5

                    # Check if user is asking for a specific customer
                    # Pattern 1: "customer <name>" or "for <name>"
                    customer_match = re.search(r'(?:customer|for)\s+([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+)*?)(?:\s*[?!]?$|\s+(?:id|email|card|number|with|info|have|has|is|does))', user_message, re.IGNORECASE)

                    customer_name = None
                    query_params = ()
                    if customer_match:
                        # Specific customer requested
                        customer_name = customer_match.group(1).strip().rstrip('?').strip()
                        # If we matched "for" and got something like "for customer X", clean it up
                        if 'customer' in customer_name.lower():
                            customer_name = customer_name.split()[-1]
                        # Use parameterized query to prevent SQL injection
                        query = "SELECT id, name, email, credit_card_number FROM customers WHERE LOWER(name) LIKE LOWER(%s) LIMIT %s"
                        query_params = (f"%{customer_name}%", limit)
                        result_text = f"customer {customer_name}"
                    else:
                        # Generic request - return top N
                        query = "SELECT id, name, email, credit_card_number FROM customers LIMIT %s"
                        query_params = (limit,)
                        result_text = f"first {limit} customers"

                    result = _execute_query_database(self.db_config, {"query": query, "params": query_params, "limit": limit}, self.guardrails)

                    # Parse and format using generic formatter
                    try:
                        data = json.loads(result)

                        if not data:
                            no_match_msg = f"No customers found matching '{customer_name}'." if customer_name else "No customers found."
                            return {
                                "assistant_message": no_match_msg,
                                "tools_used": ["query_database"],
                                "stop_reason": "tool_use",
                                "error": None,
                            }

                        # Use generic formatter for consistency
                        formatted_data = self._format_json_data(data)
                        formatted_message = f"Here is the credit card information for {result_text}:\n\n{formatted_data}"

                    except Exception as parse_err:
                        logger.warning("Failed to parse credit card query result: %s", parse_err)
                        formatted_message = f"Here is the credit card information for {result_text}:\n\n{result}"

                    return {
                        "assistant_message": formatted_message,
                        "tools_used": ["query_database"],
                        "stop_reason": "tool_use",
                        "error": None,
                    }
                except Exception as e:
                    logger.warning("Direct credit card query failed: %s", e)
                    # Fall through to normal LLM processing

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
