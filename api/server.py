"""FastAPI server: exposes the monitoring agent's HTTP API on port 8080."""

import logging
import os
import signal
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, field_validator

from api.auth import LoginRequest, Token, ChangePasswordRequest, CreateUserRequest, authenticate_user, create_access_token, verify_token, change_user_password, get_current_user, verify_token_payload, validate_password_strength
from api.rate_limiter import login_limiter, user_creation_limiter, get_client_ip
from api.audit_log import log_login_attempt, log_user_creation, log_password_change, log_user_deletion, log_user_update

logger = logging.getLogger(__name__)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

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

# Secure CORS configuration - restrict to specific origins
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
cors_origins = [origin.strip() for origin in cors_origins]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(","),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(SecurityHeadersMiddleware)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class HITLDecision(BaseModel):
    decision: str  # "approve" | "reject" | "escalate"
    notes: str = ""


class ChatMessage(BaseModel):
    message: str


class ChatbotConfigUpdate(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None
    guardrails: dict | None = None
    enabled: bool | None = None


class UpdateUserRequest(BaseModel):
    password: str | None = None
    role: str | None = None
    enabled: bool | None = None

    @field_validator('password')
    @classmethod
    def password_valid(cls, v):
        if v is not None:
            validate_password_strength(v)
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    enabled: bool
    roles: list[str]
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/login")
def login(login_request: LoginRequest, http_request: Request) -> Token:
    """Authenticate user and return JWT token."""
    # Rate limiting: 5 attempts per minute per IP
    client_ip = get_client_ip(http_request)
    if not login_limiter.is_allowed(client_ip):
        log_login_attempt(login_request.username, False, client_ip, "Rate limit exceeded")
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again later.",
        )

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        if not authenticate_user(session, login_request.username, login_request.password):
            log_login_attempt(login_request.username, False, client_ip, "Invalid credentials")
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password",
            )
        log_login_attempt(login_request.username, True, client_ip)
    finally:
        session.close()

    access_token = create_access_token(data={"sub": login_request.username})
    return Token(access_token=access_token, token_type="bearer")


@app.get("/api/me")
def get_current_user_info(username: str = Depends(verify_token)):
    """Get current authenticated user's information."""
    from store.user_models import User

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            enabled=user.enabled,
            roles=[r.name for r in user.roles],
            created_at=user.created_at.isoformat() if user.created_at else None,
        )
    finally:
        session.close()


@app.post("/api/change-password")
def change_password(request: ChangePasswordRequest, username: str = Depends(verify_token), http_request: Request = None):
    """Change user's password."""
    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        change_user_password(session, username, request.current_password, request.new_password)

        # Audit logging
        client_ip = get_client_ip(http_request) if http_request else "unknown"
        log_password_change(username, username, client_ip)

        return {"message": "Password changed successfully"}
    finally:
        session.close()


@app.post("/api/users")
def create_user(request: CreateUserRequest, username: str = Depends(verify_token), http_request: Request = None):
    """Create a new user (requires manage_users permission)."""
    from store.user_models import User, Role

    # Rate limiting: 10 attempts per minute per IP
    if http_request:
        client_ip = get_client_ip(http_request)
        if not user_creation_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Too many user creation attempts. Please try again later.",
            )

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        # Check if user has manage_users permission
        current_user = session.query(User).filter(User.username == username).first()
        if not current_user or not current_user.has_permission("manage_users"):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: manage_users required",
            )

        # Check if username already exists
        existing = session.query(User).filter(User.username == request.username).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already exists",
            )

        # Create new user
        new_user = User(username=request.username)
        new_user.set_password(request.password)

        # Assign role
        role = session.query(Role).filter(Role.name == request.role).first()
        if role:
            new_user.roles.append(role)

        session.add(new_user)
        session.commit()

        # Audit logging
        role_name = request.role if request.role else "dashboard"
        log_user_creation(username, request.username, role_name, client_ip if http_request else "unknown")

        logger.info(f"User created: {request.username}")
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            enabled=new_user.enabled,
            roles=[r.name for r in new_user.roles],
            created_at=new_user.created_at.isoformat() if new_user.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create user",
        )
    finally:
        session.close()


@app.get("/api/users")
def list_users(username: str = Depends(verify_token)):
    """List all users (requires manage_users permission)."""
    from store.user_models import User

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        # Check if user has manage_users permission
        current_user = session.query(User).filter(User.username == username).first()
        if not current_user or not current_user.has_permission("manage_users"):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: manage_users required",
            )

        users = session.query(User).all()
        return [
            UserResponse(
                id=u.id,
                username=u.username,
                enabled=u.enabled,
                roles=[r.name for r in u.roles],
                created_at=u.created_at.isoformat() if u.created_at else None,
            )
            for u in users
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list users",
        )
    finally:
        session.close()


@app.put("/api/users/{user_id}")
def update_user(user_id: int, request: UpdateUserRequest, username: str = Depends(verify_token)):
    """Update a user (requires manage_users permission)."""
    from store.user_models import User, Role

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        # Check if user has manage_users permission
        current_user = session.query(User).filter(User.username == username).first()
        if not current_user or not current_user.has_permission("manage_users"):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: manage_users required",
            )

        # Find user to update
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        # Update password if provided
        if request.password:
            user.set_password(request.password)

        # Update enabled status if provided
        if request.enabled is not None:
            user.enabled = request.enabled

        # Update role if provided
        if request.role:
            user.roles.clear()
            role = session.query(Role).filter(Role.name == request.role).first()
            if role:
                user.roles.append(role)

        session.commit()
        logger.info(f"User updated: {user.username}")

        return UserResponse(
            id=user.id,
            username=user.username,
            enabled=user.enabled,
            roles=[r.name for r in user.roles],
            created_at=user.created_at.isoformat() if user.created_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user",
        )
    finally:
        session.close()


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, username: str = Depends(verify_token)):
    """Delete a user (requires manage_users permission)."""
    from store.user_models import User

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    session = session_factory()
    try:
        # Check if user has manage_users permission
        current_user = session.query(User).filter(User.username == username).first()
        if not current_user or not current_user.has_permission("manage_users"):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: manage_users required",
            )

        # Find user to delete
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        # Prevent deleting the current user
        if user.username == username:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own user account",
            )

        session.delete(user)
        session.commit()
        logger.info(f"User deleted: {user.username}")

        return {"message": f"User {user.username} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user",
        )
    finally:
        session.close()


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
def get_agent_status(_: str = Depends(verify_token)):
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

    last_cycle = None
    if orch:
        last_cycle = getattr(orch, "_last_cycle_time", None) or _state.get("started_at")

    return {
        "last_cycle": last_cycle,
        "domains_executed": domains_executed,
        "tools_executed": [],
        "queue_size": queue_size,
        "status": "healthy" if orch else "stopped",
    }


@app.get("/api/database/{db_id}/summary")
def get_db_summary(db_id: str, _: str = Depends(verify_token)):
    """Returns a snapshot of key database metrics from the PostgreSQL adapter."""
    config = _state.get("config", {})
    db_cfg = config.get("monitored_db", {})
    try:
        from orchestrator.postgres_adapter import PostgreSQLAdapter
        adapter = PostgreSQLAdapter(
            host=db_cfg.get("host", "10.0.1.189"),
            port=int(db_cfg.get("port", 5432)),
            database=db_cfg.get("database", "shopdb"),
            user=db_cfg.get("user", "monitoring"),
            password=db_cfg.get("password", ""),
        )
        conns = adapter.get_connections()
        disk = adapter.get_disk_usage()
        slow = adapter.get_slow_queries(threshold_ms=100)
        latencies = sorted([q.get("mean_time_ms", 0) for q in slow]) if slow else [0]
        p50 = latencies[len(latencies) // 2] if latencies else 0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
        return {
            "db_id": db_id,
            "connections": conns.get("active", 0),
            "connections_max": conns.get("max_connections", 100),
            "connections_pct": conns.get("percent", 0),
            "query_latency_ms": {"p50": round(p50, 1), "p95": round(p95, 1), "p99": round(p99, 1)},
            "disk_size_gb": disk.get("size_gb", 0),
            "disk_free_gb": round(200 - disk.get("size_gb", 0), 2),
            "disk_trend_gb_per_day": 0.1,
            "ram_pct": 0,
        }
    except Exception as exc:
        logger.error("db summary failed: %s", exc)
        return {"db_id": db_id, "error": str(exc)}


@app.get("/api/insights/pending")
def get_pending_insights(_: str = Depends(verify_token)):
    """Returns pending insights grouped by domain."""
    session_factory = _state.get("session_factory")
    if not session_factory:
        return {"capacity": [], "performance": [], "locks": [], "total_pending": 0}

    from store.repository import Repository

    session = session_factory()
    try:
        import json as _json

        def _parse(desc):
            try:
                return _json.loads(desc) if desc else {}
            except Exception:
                return {}

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
                    "data": _parse(r.description),
                }
                for r in rows
            ]
            total += len(rows)
        result["total_pending"] = total
        return result
    finally:
        session.close()


@app.get("/api/activity")
def get_activity(limit: int = 30, _: str = Depends(verify_token)):
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
def approve_action(action_id: str, body: HITLDecision, _: str = Depends(verify_token)):
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


@app.get("/api/incidents/timeline")
def get_incidents_timeline(hours: int = 24, _: str = Depends(verify_token)):
    """Returns timeline of incidents (critical/warning events) for the past N hours."""
    session_factory = _state.get("session_factory")
    if not session_factory:
        return {"timeline": [], "hours": hours, "total_incidents": 0}

    # Validate hours parameter
    hours = max(1, min(hours, 720))  # Clamp to 1-720 hours

    from store.repository import Repository

    session = session_factory()
    try:
        repo = Repository(session)
        timeline = repo.get_incidents_timeline(hours=hours)
        total_incidents = sum(b["total_count"] for b in timeline)
        return {
            "timeline": timeline,
            "hours": hours,
            "total_incidents": total_incidents,
        }
    finally:
        session.close()


@app.get("/api/hitl/pending")
def get_pending_hitl_actions(_: str = Depends(verify_token)):
    """Returns pending HITL (human-in-the-loop) action queue items."""
    session_factory = _state.get("session_factory")
    if not session_factory:
        return {"actions": [], "total_pending": 0}

    from store.repository import Repository

    session = session_factory()
    try:
        repo = Repository(session)
        actions = repo.get_pending_actions(limit=50)
        return {
            "actions": [
                {
                    "id": a.id,
                    "domain": a.domain,
                    "action_type": a.action_type,
                    "risk_level": a.risk_level,
                    "payload": a.payload,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in actions
            ],
            "total_pending": repo.count_pending_approvals(),
        }
    finally:
        session.close()


@app.get("/api/config/domains")
def get_config_domains(_: str = Depends(verify_token)):
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
# Chatbot routes
# ---------------------------------------------------------------------------


@app.get("/api/chatbot/config")
def get_chatbot_config(_: str = Depends(verify_token)):
    """Get current chatbot configuration."""
    from store.chatbot_models import ChatbotConfig

    session_factory = _state.get("session_factory")
    if not session_factory:
        return {"error": "Database not available"}

    session = session_factory()
    try:
        config = session.query(ChatbotConfig).first()
        if config:
            return config.to_dict()
        else:
            # Return default config
            return {
                "llm_provider": "anthropic",
                "llm_model": "claude-3-5-sonnet-20241022",
                "system_prompt": """You are a database assistant for the 'shopdb' PostgreSQL database. You help users query and analyze data.

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
- If data is sensitive or unusual, flag it for the user""",
                "tools": ["query_database", "get_metrics", "get_slow_queries", "get_table_stats", "check_locks"],
                "guardrails": {
                    "allow_writes": False,
                    "allow_ddl": False,
                    "query_timeout_seconds": 5,
                    "max_rows_return": 1000,
                },
                "enabled": True,
            }
    finally:
        session.close()


@app.post("/api/chatbot/config")
def update_chatbot_config(
    config_update: ChatbotConfigUpdate, _: str = Depends(verify_token)
):
    """Update chatbot configuration (admin function)."""
    from store.chatbot_models import ChatbotConfig

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    session = session_factory()
    try:
        config = session.query(ChatbotConfig).first()
        if not config:
            config = ChatbotConfig()

        for key, value in config_update.dict(exclude_unset=True).items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)

        session.add(config)
        session.commit()
        logger.info("Chatbot config updated")
        return {"success": True, "config": config.to_dict()}
    except Exception as exc:
        session.rollback()
        logger.error("Chatbot config update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update config")
    finally:
        session.close()


@app.post("/api/chatbot/chat")
def chat_with_bot(message: ChatMessage, _: str = Depends(verify_token)):
    """Send a message to the chatbot."""
    from store.chatbot_models import ChatbotConfig, ChatMessage as ChatMessageModel
    from orchestrator.chatbot_service import ChatbotService
    import os

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    session = session_factory()
    try:
        config_row = session.query(ChatbotConfig).first()
        config = config_row.to_dict() if config_row else {}

        # Check if API key is set for the configured provider
        provider = config.get("llm_provider", "anthropic")
        api_key_env_var = f"{provider.upper()}_API_KEY"
        if not os.environ.get(api_key_env_var):
            raise HTTPException(status_code=503, detail="API key not configured")

        # Get monitored DB config
        db_config = _state.get("config", {}).get("monitored_db", {})

        # Create chatbot service and get response
        service = ChatbotService(config, db_config)
        response = service.chat(message.message)

        # Store in history
        msg_record = ChatMessageModel(
            user_message=message.message,
            assistant_message=response.get("assistant_message", ""),
            tools_used=response.get("tools_used", []),
        )
        session.add(msg_record)
        session.commit()

        return response
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.error("Chatbot error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        session.close()


@app.get("/api/chatbot/history")
def get_chat_history(limit: int = 50, _: str = Depends(verify_token)):
    """Get chat message history."""
    from store.chatbot_models import ChatMessage as ChatMessageModel

    session_factory = _state.get("session_factory")
    if not session_factory:
        return []

    session = session_factory()
    try:
        messages = (
            session.query(ChatMessageModel)
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [msg.to_dict() for msg in reversed(messages)]
    finally:
        session.close()


@app.delete("/api/chatbot/history")
def clear_chat_history(_: str = Depends(verify_token)):
    """Clear all chat message history."""
    from store.chatbot_models import ChatMessage as ChatMessageModel

    session_factory = _state.get("session_factory")
    if not session_factory:
        return {"message": "Chat history cleared"}

    session = session_factory()
    try:
        session.query(ChatMessageModel).delete()
        session.commit()
        return {"message": "Chat history cleared"}
    finally:
        session.close()


@app.get("/api/chatbot/tools")
def get_available_tools(_: str = Depends(verify_token)):
    """Get list of available chatbot tools."""
    from orchestrator.chatbot_service import AVAILABLE_TOOLS

    return AVAILABLE_TOOLS


@app.get("/api/chatbot/models")
def get_available_models(provider: str = "anthropic", _: str = Depends(verify_token)):
    """Get list of available models for the specified LLM provider."""
    models_by_provider = {
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20250219",
            "claude-3-haiku-20240307",
        ],
        "google": [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-pro",
        ],
        "openai": [
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
        ],
    }

    return {
        "provider": provider,
        "models": models_by_provider.get(provider.lower(), []),
    }


@app.get("/api/chatbot/guardrails")
def get_chatbot_guardrails(_: str = Depends(verify_token)):
    """Get current safety guardrails."""
    from store.chatbot_models import ChatbotConfig

    session_factory = _state.get("session_factory")
    if not session_factory:
        return {}

    session = session_factory()
    try:
        config = session.query(ChatbotConfig).first()
        return config.guardrails if config else {}
    finally:
        session.close()


@app.post("/api/chatbot/prisma-airs/toggle")
def toggle_prisma_airs(_: str = Depends(verify_token)):
    """Toggle Prisma AIRS scanning on/off for demo purposes."""
    from store.chatbot_models import ChatbotConfig

    session_factory = _state.get("session_factory")
    if not session_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    session = session_factory()
    try:
        config = session.query(ChatbotConfig).first()
        if not config:
            raise HTTPException(status_code=404, detail="Chatbot config not found")

        config.prisma_airs_enabled = not config.prisma_airs_enabled
        session.commit()

        return {
            "prisma_airs_enabled": config.prisma_airs_enabled,
            "message": f"Prisma AIRS is now {'enabled' if config.prisma_airs_enabled else 'disabled'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("Error toggling Prisma AIRS: %s", e)
        raise HTTPException(status_code=500, detail="Failed to toggle Prisma AIRS")
    finally:
        session.close()


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
