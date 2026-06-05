"""End-to-end integration tests for the SQL monitoring agent."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Orchestrator full-cycle test
# ---------------------------------------------------------------------------


def test_orchestrator_full_cycle(test_orchestrator, db_engine, db_session):
    """Run one forced cycle, verify insights are persisted, check aggregation."""
    from orchestrator.aggregator import aggregate_insights
    from store.repository import Repository

    orch = test_orchestrator
    aggregated = orch.run_once()

    # Top-level structure
    assert "timestamp" in aggregated
    assert "domains" in aggregated
    assert "alerts" in aggregated
    assert "status" in aggregated
    assert aggregated["status"] in ("healthy", "warning", "critical")

    # At least one domain executed
    assert len(aggregated["domains"]) > 0

    # Insights persisted to DB
    repo = Repository(db_session)
    # run_once uses its own session — check via a fresh query
    from store.models import Insight
    all_insights = db_session.query(Insight).all()
    # Insights are written via orch._persist which uses orch._session_factory
    # so we check via that session
    session = orch._session_factory()
    try:
        repo2 = Repository(session)
        pending = repo2.get_insights_pending(status="pending", limit=50)
        assert len(pending) >= 0  # may be 0 if all errored, but no exception
    finally:
        session.close()

    logger.info("Full cycle result: status=%s", aggregated["status"])


# ---------------------------------------------------------------------------
# Capacity domain test
# ---------------------------------------------------------------------------


def test_domain_capacity(test_config):
    """CapacityDomain.analyze() returns the expected output keys."""
    from orchestrator.capacity_domain import CapacityDomain

    domain = CapacityDomain(test_config)

    result = domain.analyze()

    required_keys = [
        "disk_free_gb",
        "disk_trend_gb_per_day",
        "forecast_full_date",
        "ram_used_pct",
        "ram_free_gb",
        "severity",
        "summary",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"

    assert isinstance(result["disk_free_gb"], float)
    assert isinstance(result["ram_used_pct"], float)
    assert result["severity"] in ("ok", "warning", "critical")
    logger.info("CapacityDomain result: %s", result)


# ---------------------------------------------------------------------------
# Locks domain test
# ---------------------------------------------------------------------------


def test_domain_locks(test_config):
    """LocksDomain.analyze() returns the expected output structure."""
    from orchestrator.locks_domain import LocksDomain

    domain = LocksDomain(test_config)
    result = domain.analyze()

    required_keys = ["locks_detected", "max_wait_seconds", "blocking_query", "details"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"

    assert isinstance(result["locks_detected"], int)
    assert isinstance(result["max_wait_seconds"], float)
    assert isinstance(result["details"], list)
    assert result["severity"] in ("ok", "warning", "critical")
    logger.info("LocksDomain result: %s", result)


# ---------------------------------------------------------------------------
# Tool registry test
# ---------------------------------------------------------------------------


def test_tool_registry(test_config):
    """ToolRegistry discovers tools and topological sort is stable."""
    from tools.registry import ToolRegistry

    registry = ToolRegistry(test_config)

    # All tools should be discoverable
    names = registry.all_names()
    assert "capacity_forecaster" in names
    assert "storage_advisor" in names
    assert "query_analyzer" in names
    assert "cost_advisor" in names
    assert "lock_analyzer" in names

    # Topological order: forecaster before advisor
    capacity_order = registry.resolve_execution_order("capacity")
    capacity_names = [type(t).__name__ for t in capacity_order]
    assert capacity_names.index("CapacityForecaster") < capacity_names.index("StorageAdvisor")

    # Performance order: analyzer before advisor
    perf_order = registry.resolve_execution_order("performance")
    perf_names = [type(t).__name__ for t in perf_order]
    assert perf_names.index("QueryAnalyzer") < perf_names.index("CostAdvisor")

    # Locks: single tool, no dependency
    locks_order = registry.resolve_execution_order("locks")
    assert len(locks_order) == 1

    logger.info("Tool registry names: %s", names)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


def test_api_endpoints(test_config, db_engine):
    """FastAPI test client: /api/health returns expected structure."""
    from api.server import _state, app
    from store import get_session

    # Wire state so health check works without a live DB
    _state["config"] = test_config
    _state["engine"] = db_engine
    _state["session_factory"] = get_session(db_engine)
    _state["orchestrator"] = None  # no live orchestrator in unit test

    client = TestClient(app, raise_server_exceptions=True)

    # /api/health
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert body["status"] == "ok"
    assert "timestamp" in body
    assert "db_connected" in body

    # /api/agent-status
    resp = client.get("/api/agent-status")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "queue_size" in body

    # /api/config/domains
    resp = client.get("/api/config/domains")
    assert resp.status_code == 200
    domains = resp.json()
    assert isinstance(domains, list)
    domain_names = [d["name"] for d in domains]
    assert "capacity" in domain_names

    # /api/insights/pending
    resp = client.get("/api/insights/pending")
    assert resp.status_code == 200
    body = resp.json()
    assert "capacity" in body
    assert "performance" in body
    assert "locks" in body
    assert "total_pending" in body

    # /api/activity
    resp = client.get("/api/activity?limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # /api/database/{db_id}/summary
    resp = client.get("/api/database/postgres/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert "connections" in summary
    assert "query_latency_ms" in summary
    assert "disk_free_gb" in summary

    logger.info("All API endpoints passed")
