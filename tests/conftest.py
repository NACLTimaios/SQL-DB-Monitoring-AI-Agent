"""pytest fixtures shared across all test modules."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config.loader import ConfigLoader
from store.models import Base


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def config_fixture():
    """Load the real config.yaml for integration tests."""
    loader = ConfigLoader()
    return loader.load("config.yaml")


@pytest.fixture(scope="session")
def test_config():
    """Return a minimal in-memory config suitable for unit tests.

    Uses SQLite so no PostgreSQL instance is required.
    """
    return {
        "domains": {
            "capacity": {
                "enabled": True,
                "class": "CapacityDomain",
                "module": "orchestrator.capacity_domain",
                "interval_seconds": 60,
                "tools": ["capacity_forecaster", "storage_advisor"],
            },
            "performance": {
                "enabled": True,
                "class": "PerformanceDomain",
                "module": "orchestrator.performance_domain",
                "interval_seconds": 300,
                "tools": ["query_analyzer", "cost_advisor"],
            },
            "locks": {
                "enabled": True,
                "class": "LocksDomain",
                "module": "orchestrator.locks_domain",
                "interval_seconds": 10,
                "tools": ["lock_analyzer"],
            },
        },
        "tools": {
            "capacity_forecaster": {
                "module": "tools.capacity_tools",
                "class": "CapacityForecaster",
                "capability_tags": ["forecasting", "trending"],
                "depends_on": [],
                "timeout_seconds": 2,
            },
            "storage_advisor": {
                "module": "tools.capacity_tools",
                "class": "StorageAdvisor",
                "capability_tags": ["recommendations"],
                "depends_on": ["capacity_forecaster"],
                "timeout_seconds": 1,
            },
            "query_analyzer": {
                "module": "tools.performance_tools",
                "class": "QueryAnalyzer",
                "capability_tags": ["query_profiling"],
                "depends_on": [],
                "timeout_seconds": 5,
            },
            "cost_advisor": {
                "module": "tools.performance_tools",
                "class": "CostAdvisor",
                "capability_tags": ["cost_analysis"],
                "depends_on": ["query_analyzer"],
                "timeout_seconds": 2,
            },
            "lock_analyzer": {
                "module": "tools.locks_tools",
                "class": "LockAnalyzer",
                "capability_tags": ["lock_analysis"],
                "depends_on": [],
                "timeout_seconds": 1,
            },
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "test_agent",
            "user": "test",
            "password": "test",
        },
        "monitored_db": {
            "host": "10.0.1.10",
            "port": 5432,
            "user": "monitoring",
            "password": "changeme",
            "database": "postgres",
        },
        "api": {"host": "0.0.0.0", "port": 8080},
        "logging": {"level": "INFO", "file": "logs/agent.log"},
    }


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite engine with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a SQLAlchemy session backed by the in-memory SQLite engine."""
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Orchestrator fixture (no real DB — only domains/config needed)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def test_orchestrator(test_config, db_engine):
    """Instantiate an Orchestrator wired to in-memory SQLite."""
    from orchestrator.domains import DomainRegistry
    from orchestrator.main import Orchestrator
    from store import get_session

    # Patch the Orchestrator to use the test engine instead of Postgres.
    orch = object.__new__(Orchestrator)
    orch._config = test_config
    orch._running = False
    orch._cycle_count = 0
    orch._engine = db_engine
    orch._session_factory = get_session(db_engine)

    registry = DomainRegistry(test_config)
    orch._domains = registry.load()
    yield orch
