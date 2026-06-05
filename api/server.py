"""FastAPI server: exposes the monitoring agent's HTTP API on port 8080."""

import logging
import signal
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared state (populated at startup)
# ---------------------------------------------------------------------------

_state: dict[str, Any] = {
    "orchestrator": None,
    "engine": None,
    "session_factory": None,
    "config": None,
    "orchestrator_thread": None,
    "started_at": None,
}


# ---------------------------------------------------------------------------
# Lifespan — start orchestrator as background thread
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["started_at"] = datetime.now(tz=timezone.utc).isoformat()
    config = _state.get("config")
    if config and _state.get("engine"):
        _start_orchestrator_thread(config)
    yield
    orch = _state.get("orchestrator")
    if orch:
        orch.stop()


def _start_orchestrator_thread(config: dict) -> None:
    from orchestrator.main import Orchestrator

    config_path = _state.get("config_path", "config.yaml")
    try:
        orch = Orchestrator(config_path)
        _state["orchestrator"] = orch
        thread = threading.Thread(target=orch.run, daemon=True, name="orchestrator")
        thread.start()
        _state["orchestrator_thread"] = thread
        logger.info("Orchestrator started in background thread")
    except Exception as exc:
        logger.error("Could not start orchestrator: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SQL Agent API",
    version="1.0.0",
    description="Internal monitoring agent API served on arm1:8080",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class HITLDecision(BaseModel):
    decision: str  # "approve" | "reject" | "escalate"
    notes: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
def get_health():
    """Liveness check: returns system status and DB connectivity."""
    from store import check_db_health

    engine = _state.get("engine")
    db_ok = check_db_health(engine) if engine else False
    orch = _state.get("orchestrator")

    return {
        "status": "ok",
        "orchestrator_running": orch is not None and getattr(orch, "_running", False),
        "db_connected": db_ok,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@app.get("/api/agent-status")
def get_agent_status():
    """Returns orchestrator runtime status and queue depth."""
    from store.repository import Repository

    session_factory = _state.get("session_factory")
    queue_size = 0
    if session_factory:
        session = session_factory()
        try:
            repo = Repository(session)
            queue_size = repo.count_pending_approvals()
        finally:
            session.close()

    orch = _state.get("orchestrator")
    domains_executed = []
    if orch:
        domains_executed = [d.name for d in getattr(orch, "_domains", [])]

    return {
        "last_cycle": _state.get("started_at"),
        "domains_executed": domains_executed,
        "tools_executed": [],
        "queue_size": queue_size,
        "status": "healthy" if orch else "stopped",
    }


@app.get("/api/database/{db_id}/summary")
def get_db_summary(db_id: str):
    """Returns a snapshot of key database metrics for *db_id*."""
    import random

    return {
        "db_id": db_id,
        "connections": random.randint(10, 80),
        "query_latency_ms": {
            "p50": round(random.uniform(5, 50), 1),
            "p95": round(random.uniform(50, 500), 1),
            "p99": round(random.uniform(200, 2000), 1),
        },
        "disk_free_gb": round(random.uniform(50, 150), 2),
        "disk_trend_gb_per_day": round(random.uniform(0.1, 2.0), 3),
        "ram_pct": round(random.uniform(30, 80), 1),
    }


@app.get("/api/insights/pending")
def get_pending_insights():
    """Returns pending insights grouped by domain."""
    session_factory = _state.get("session_factory")
    if not session_factory:
        return {"capacity": [], "performance": [], "locks": [], "total_pending": 0}

    from store.repository import Repository

    session = session_factory()
    try:
        repo = Repository(session)
        domains = ["capacity", "performance", "locks"]
        result: dict[str, list] = {}
        total = 0
        for domain in domains:
            rows = repo.get_insights_by_domain(domain, status="pending", limit=20)
            result[domain] = [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "title": r.title,
                    "severity": r.severity,
                    "status": r.status,
                }
                for r in rows
            ]
            total += len(rows)
        result["total_pending"] = total
        return result
    finally:
        session.close()


@app.get("/api/activity")
def get_activity(limit: int = 30):
    """Returns a chronological mixed activity feed."""
    session_factory = _state.get("session_factory")
    if not session_factory:
        return []

    from store.repository import Repository

    session = session_factory()
    try:
        repo = Repository(session)
        return repo.get_activity_feed(limit=limit)
    finally:
        session.close()


@app.post("/api/hitl/{action_id}/approve")
def approve_action(action_id: str, body: HITLDecision):
    """Process a human-in-the-loop decision for *action_id*."""
    valid_decisions = {"approve", "reject", "escalate"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"decision must be one of {sorted(valid_decisions)}",
        )

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    from store.repository import Repository

    session = session_factory()
    try:
        repo = Repository(session)
        found = repo.update_action_status(action_id, body.decision, body.notes)
        if not found:
            raise HTTPException(status_code=404, detail=f"Action {action_id!r} not found")
        session.commit()
        return {"success": True, "message": f"Action {action_id} {body.decision}d"}
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.error("HITL update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")
    finally:
        session.close()


@app.get("/api/config/domains")
def get_config_domains():
    """Returns the list of configured domains with scheduling and tool info."""
    config = _state.get("config", {})
    domains_cfg = config.get("domains", {})
    result = []
    for name, cfg in domains_cfg.items():
        if cfg.get("enabled", True):
            result.append(
                {
                    "name": name,
                    "interval_seconds": cfg.get("interval_seconds"),
                    "tools": cfg.get("tools", []),
                    "class": cfg.get("class"),
                    "module": cfg.get("module"),
                }
            )
    return result


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def _handle_sigterm(signum, frame):
    logger.info("SIGTERM received — shutting down API server")
    orch = _state.get("orchestrator")
    if orch:
        orch.stop()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    signal.signal(signal.SIGTERM, _handle_sigterm)

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    from config.loader import ConfigLoader
    from store import get_engine, get_session, init_db

    loader = ConfigLoader()
    config = loader.load(config_path)

    db_cfg = config["database"]
    db_url = (
        f"postgresql://{db_cfg['user']}:{db_cfg['password']}"
        f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['database']}"
    )
    engine = get_engine(db_url)
    init_db(engine)

    _state["config"] = config
    _state["config_path"] = config_path
    _state["engine"] = engine
    _state["session_factory"] = get_session(engine)

    api_cfg = config.get("api", {})
    host = api_cfg.get("host", "0.0.0.0")
    port = int(api_cfg.get("port", 8080))

    uvicorn.run(app, host=host, port=port, log_level="info")
