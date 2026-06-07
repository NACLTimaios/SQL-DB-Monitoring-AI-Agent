# SQL Agent System Architecture

## Complete System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           INTERNET / USER BROWSERS                                      │
│                                                                                         │
│                        https://sqlagent.dittmar.it                                     │
└────────────────────────────────────┬────────────────────────────────────────────────────┘
                                     │ HTTPS (Let's Encrypt)
                                     │
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          ARM2 (Frontend Server)                                        │
│                        IP: 10.0.2.11 (OCI)                                            │
│ ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│ │ NGINX (Reverse Proxy)                                                           │  │
│ │  - Port 443 (HTTPS)                                                             │  │
│ │  - Routes /api/* → arm1:8084                                                    │  │
│ │  - Serves /var/www/dashboard                                                   │  │
│ └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                  │                                                    │
│ ┌──────────────────────────────────┴────────────────────────────────────────────────┐ │
│ │ React Dashboard (SPA)                                                            │ │
│ │  ├─ App.tsx (Authentication, routing)                                           │ │
│ │  ├─ Login.tsx (JWT login form)                                                  │ │
│ │  ├─ AdminPage.tsx (LLM config, model switching)                                 │ │
│ │  ├─ Components/                                                                 │ │
│ │  │  ├─ Header.tsx (Navigation, logout)                                         │ │
│ │  │  ├─ ChatBot.tsx (Chat interface)                                            │ │
│ │  │  ├─ AgentHealthPanel.tsx (Status display)                                   │ │
│ │  │  ├─ CapacityPanel.tsx (Capacity insights)                                   │ │
│ │  │  ├─ PerformancePanel.tsx (Slow queries)                                     │ │
│ │  │  ├─ LocksPanel.tsx (Lock detection)                                         │ │
│ │  │  ├─ DatabaseSummaryPanel.tsx (Connections, latency, disk)                   │ │
│ │  │  ├─ InsightsAlerts.tsx (Critical alerts)                                    │ │
│ │  │  ├─ ActivityFeed.tsx (Recent activity)                                      │ │
│ │  │  └─ [Other panels...]                                                       │ │
│ │  └─ Utils/                                                                      │ │
│ │     ├─ api.ts (Axios calls, JWT handling)                                      │ │
│ │     └─ format.ts (Date/number formatting)                                      │ │
│ │                                                                                 │ │
│ │ Storage: localStorage (JWT token)                                              │ │
│ └─────────────────────────────────────┬──────────────────────────────────────────┘ │
│                                       │ API calls (Bearer token)                    │
└───────────────────────────────────────┼───────────────────────────────────────────┘
                                        │ HTTP/REST (port 8084)
                                        │
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                          ARM1 (Backend Server)                                       │
│                      IP: 10.0.2.176 (OCI)                                           │
│                                                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│ │ FastAPI Server (Port 8084)                                                     │ │
│ │                                                                                 │ │
│ │ Authentication Endpoints:                                                       │ │
│ │  POST /api/login                                                               │ │
│ │       → authenticate_user(username, password)                                  │ │
│ │       ← {access_token, token_type}                                             │ │
│ │                                                                                 │ │
│ │ Public Endpoints (No Auth):                                                     │ │
│ │  GET /api/health                                                               │ │
│ │      ← {status, orchestrator_running, db_connected, timestamp}                 │ │
│ │                                                                                 │ │
│ │ Protected Endpoints (JWT Required):                                            │ │
│ │ Dashboard Endpoints:                                                            │ │
│ │  GET /api/agent-status                                                         │ │
│ │      ← {last_cycle, domains_executed, queue_size, status}                      │ │
│ │  GET /api/database/{db_id}/summary                                             │ │
│ │      ← {connections, disk_size, latency_ms, ...}                               │ │
│ │  GET /api/insights/pending                                                     │ │
│ │      ← {capacity: [...], performance: [...], locks: [...]}                     │ │
│ │  GET /api/activity?limit=30                                                    │ │
│ │      ← [{type, timestamp, title, severity}, ...]                               │ │
│ │                                                                                 │ │
│ │ Chatbot Endpoints:                                                              │ │
│ │  GET  /api/chatbot/config                                                      │ │
│ │  POST /api/chatbot/config                                                      │ │
│ │  POST /api/chatbot/chat                                                        │ │
│ │  GET  /api/chatbot/history?limit=50                                            │ │
│ │  GET  /api/chatbot/tools                                                       │ │
│ │  GET  /api/chatbot/models?provider={provider}                                  │ │
│ │  GET  /api/chatbot/guardrails                                                  │ │
│ │                                                                                 │ │
│ │ Other Endpoints:                                                                │ │
│ │  GET /api/hitl/pending                                                         │ │
│ │  POST /api/hitl/{action_id}/approve                                            │ │
│ │  GET /api/incidents-timeline?hours=24                                          │ │
│ │  GET /api/config/domains                                                       │ │
│ └────────────┬────────────────────────────┬──────────────────────┬────────────────┘ │
│              │                            │                      │                  │
│              ▼                            ▼                      ▼                  │
│ ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────┐ │
│ │ LLM Provider Layer   │  │ Orchestrator Loop    │  │ User Management          │ │
│ │                      │  │                      │  │                          │ │
│ │ ├─ Anthropic Claude  │  │ ├─ Capacity Domain   │  │ ├─ authenticate_user()   │ │
│ │ ├─ Google Gemini     │  │ │  (60s interval)    │  │ ├─ verify_token()        │ │
│ │ ├─ OpenAI GPT        │  │ ├─ Performance Domain│  │ ├─ create_access_token() │ │
│ │                      │  │ │  (300s interval)   │  │ ├─ Password hashing      │ │
│ │ Tool Execution:      │  │ ├─ Locks Domain     │  │ │  (Argon2)              │ │
│ │ ├─ query_database    │  │ │  (10s interval)    │  │ ├─ JWT tokens (24h exp)  │ │
│ │ ├─ get_metrics       │  │ │                    │  │ │                        │ │
│ │ ├─ get_slow_queries  │  │ └─ PostgreSQL Adapter│  │ └─ Permission system     │ │
│ │ ├─ get_table_stats   │  │    (psycopg2)        │  │                          │ │
│ │ └─ check_locks       │  │                      │  │ Roles:                   │ │
│ │                      │  │ Domains save results │  │ ├─ admin (full access)   │ │
│ │ Provider Switching:  │  │ to local database     │  │ └─ dashboard (read-only) │ │
│ │ ├─ llm_providers.py  │  │                      │  │                          │ │
│ │ ├─ Factory pattern   │  │ Tools:               │  │ Storage:                 │ │
│ │ └─ Provider-agnostic │  │ ├─ CapacityForecaster│  │ ├─ User table            │ │
│ │   chatbot_service.py │  │ ├─ QueryAnalyzer    │  │ ├─ Role table            │ │
│ │                      │  │ ├─ LockAnalyzer     │  │ ├─ Permission table      │ │
│ │                      │  │ └─ StorageAdvisor   │  │ └─ UserProfile table     │ │
│ └──────────────────────┘  └──────────────────────┘  └──────────────────────────┘ │
│                                                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Agent Store Database (PostgreSQL 14)                                           │ │
│ │ Host: localhost:5432                                                           │ │
│ │ Database: agent_store                                                          │ │
│ │ User: agent                                                                    │ │
│ │                                                                                 │ │
│ │ Tables:                                                                         │ │
│ │  ├─ observation (domain metrics, timestamps)                                   │ │
│ │  ├─ analysis (analyzed observations, insights)                                 │ │
│ │  ├─ insight (actionable insights, severity levels)                             │ │
│ │  ├─ action_queue (pending human-in-the-loop actions)                           │ │
│ │  ├─ chatbot_config (LLM provider, model, system prompt)                        │ │
│ │  ├─ chat_message (chatbot conversation history)                                │ │
│ │  ├─ user (username, password_hash, enabled flag)                               │ │
│ │  ├─ role (admin, dashboard roles)                                              │ │
│ │  ├─ permission (view_dashboard, manage_users, etc.)                            │ │
│ │  └─ user_profile (custom profile data - JSON)                                  │ │
│ └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
└────────────────────────────────────┬────────────────────────────────────────────────┘
                                     │ psycopg2 (Read-only monitoring user)
                                     │
┌────────────────────────────────────────────────────────────────────────────────────┐
│                       VM1 (Monitored Database)                                     │
│                    IP: 10.0.1.189 (Data Center)                                   │
│                                                                                    │
│ ┌──────────────────────────────────────────────────────────────────────────────┐  │
│ │ PostgreSQL 16 (shopdb)                                                       │  │
│ │ Port: 5432                                                                   │  │
│ │ Monitoring User: monitoring (pg_monitor role)                                │  │
│ │                                                                               │  │
│ │ Extensions:                                                                  │  │
│ │  ├─ pg_stat_statements (query performance tracking)                          │  │
│ │                                                                               │  │
│ │ Schema:                                                                      │  │
│ │  ├─ customer (production data)                                               │  │
│ │  ├─ product (production data)                                                │  │
│ │  ├─ order (production data)                                                  │  │
│ │  └─ pg_stat_statements views (performance metrics)                           │  │
│ │                                                                               │  │
│ │ Monitoring Points:                                                           │  │
│ │  ├─ pg_stat_activity (active sessions, blocking info)                        │  │
│ │  ├─ pg_stat_statements (slow queries)                                        │  │
│ │  ├─ pg_locks (lock contention)                                               │  │
│ │  ├─ pg_database_size (disk usage)                                            │  │
│ │  └─ max_connections (connection limits)                                      │  │
│ └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ pgbench (load generation)
                                     │
┌────────────────────────────────────────────────────────────────────────────────────┐
│                       VM2 (Load Generator)                                         │
│                                                                                    │
│  pgbench (runs every 2 hours via systemd timer)                                   │
│  ├─ 5-20 concurrent clients                                                      │
│  ├─ Varying transaction rates                                                    │
│  └─ Generates realistic, fluctuating workloads for monitoring                     │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## API Endpoints Reference

### Authentication
```
POST /api/login
  Request:  {username: "admin", password: "changeme"}
  Response: {access_token: "...", token_type: "bearer"}
  Status:   200 (success) | 401 (invalid credentials) | 500 (DB error)
```

### Health & Status
```
GET /api/health
  No Auth Required
  Response: {
    status: "ok",
    orchestrator_running: true,
    db_connected: true,
    timestamp: "2026-06-07T..."
  }

GET /api/agent-status
  Auth Required: Bearer token
  Response: {
    last_cycle: "2026-06-07T...",
    domains_executed: ["capacity", "performance", "locks"],
    tools_executed: [],
    queue_size: 3128,
    status: "healthy"
  }
```

### Dashboard Data
```
GET /api/database/1/summary
  Auth Required
  Response: {
    db_id: "1",
    connections: 4,
    connections_max: 100,
    connections_pct: 4,
    query_latency_ms: {p50: 285.2, p95: 455.2, p99: 455.2},
    disk_size_gb: 0.026,
    disk_free_gb: 199.974,
    disk_trend_gb_per_day: 0.1,
    ram_pct: 0
  }

GET /api/insights/pending
  Auth Required
  Response: {
    capacity: [{id, timestamp, title, severity, status, data}, ...],
    performance: [...],
    locks: [...],
    total_pending: 60
  }

GET /api/activity?limit=30
  Auth Required
  Response: [
    {
      type: "insight",
      timestamp: "2026-06-07T...",
      domain: "locks",
      title: "Locks: No contention",
      severity: "ok",
      status: "pending"
    },
    ...
  ]
```

### Chatbot Configuration
```
GET /api/chatbot/config
  Auth Required
  Response: {
    llm_provider: "anthropic",
    llm_model: "claude-3-5-sonnet",
    system_prompt: "You are a helpful database expert...",
    tools: ["query_database", "get_metrics", ...],
    guardrails: {
      allow_writes: false,
      allow_ddl: false,
      query_timeout_seconds: 5,
      max_rows_return: 1000,
      restricted_tables: []
    },
    enabled: true
  }

POST /api/chatbot/config
  Auth Required (admin only)
  Request: {
    llm_provider: "google",
    llm_model: "gemini-2.5-flash",
    ... (other fields)
  }
  Response: {success: true}

GET /api/chatbot/models?provider=anthropic
  Auth Required
  Response: {
    models: [
      "claude-3-5-sonnet-20241022",
      "claude-3-opus-20240229",
      "claude-3-haiku-20240307"
    ]
  }
```

### Chatbot Interaction
```
POST /api/chatbot/chat
  Auth Required
  Request: {message: "How many customers are in the database?"}
  Response: {
    response: "There are 500 customers...",
    tools_used: ["query_database"],
    timestamp: "2026-06-07T..."
  }

GET /api/chatbot/history?limit=50
  Auth Required
  Response: [
    {
      id: "...",
      user_message: "...",
      assistant_response: "...",
      timestamp: "...",
      tools_used: [...]
    },
    ...
  ]

GET /api/chatbot/tools
  Auth Required
  Response: {
    query_database: {
      description: "Execute SELECT queries",
      parameters: {query: "SQL query string", ...}
    },
    get_metrics: {
      description: "Get database metrics",
      parameters: {...}
    },
    ...
  }

GET /api/chatbot/guardrails
  Auth Required
  Response: {
    allow_writes: false,
    allow_ddl: false,
    query_timeout_seconds: 5,
    max_rows_return: 1000,
    restricted_tables: []
  }
```

## Component Dependency Graph

```
Frontend (React/TypeScript)
├─ App.tsx (root)
│  ├─ App Routes
│  │  ├─ Login.tsx ──────────────→ POST /api/login
│  │  └─ Dashboard
│  │     ├─ Header.tsx
│  │     │  └─ logout() ──────────→ localStorage.clear()
│  │     ├─ AgentHealthPanel ◄───── GET /api/health
│  │     ├─ CapacityPanel ◄───────── GET /api/insights/pending
│  │     ├─ PerformancePanel ◄────── GET /api/insights/pending
│  │     ├─ LocksPanel ◄──────────── GET /api/insights/pending
│  │     ├─ DatabaseSummaryPanel ◄── GET /api/database/1/summary
│  │     ├─ InsightsAlerts ◄──────── GET /api/insights/pending
│  │     ├─ ActivityFeed ◄────────── GET /api/activity
│  │     ├─ ChatBot.tsx ◄───────────→ POST /api/chatbot/chat
│  │     │                         ├─ GET /api/chatbot/history
│  │     │                         ├─ GET /api/chatbot/config
│  │     │                         └─ GET /api/chatbot/tools
│  │     │
│  │     └─ AdminPage.tsx ◄────────→ GET /api/chatbot/config
│  │                              ├─ POST /api/chatbot/config
│  │                              ├─ GET /api/chatbot/tools
│  │                              └─ GET /api/chatbot/models
│  │
│  └─ utils/api.ts (all HTTP calls)
│     └─ utils/format.ts (formatting)

Backend (Python/FastAPI)
├─ main.py (CLI entry point)
│  └─ run command
│     ├─ api/server.py (FastAPI app + routes)
│     │  ├─ api/auth.py (authentication)
│     │  │  ├─ verify_token() (JWT validation)
│     │  │  ├─ authenticate_user() (password check)
│     │  │  ├─ create_access_token() (JWT creation)
│     │  │  └─ bootstrap_roles_and_permissions() (setup)
│     │  │
│     │  └─ store/ (database layer)
│     │     ├─ __init__.py (engine/session factory)
│     │     ├─ models.py (observation/analysis/insight)
│     │     ├─ chatbot_models.py (config/chat history)
│     │     ├─ user_models.py (user/role/permission)
│     │     └─ repository.py (queries)
│     │
│     └─ orchestrator/main.py (background loop)
│        ├─ orchestrator/domains.py (capacity/perf/locks)
│        │  └─ orchestrator/postgres_adapter.py
│        │     └─ psycopg2 (vm1:5432 connection)
│        │
│        ├─ orchestrator/llm_providers.py
│        │  ├─ AnthropicProvider
│        │  │  └─ anthropic SDK (api.anthropic.com)
│        │  ├─ GoogleProvider
│        │  │  └─ google-generativeai SDK
│        │  └─ OpenAIProvider
│        │     └─ openai SDK (api.openai.com)
│        │
│        ├─ orchestrator/chatbot_service.py
│        │  └─ Tool executors (database queries)
│        │
│        └─ tools/registry.py
│           ├─ CapacityForecaster
│           ├─ QueryAnalyzer
│           └─ LockAnalyzer

Databases
├─ agent_store (arm1:5432)
│  ├─ observation (raw metrics)
│  ├─ analysis (tool results)
│  ├─ insight (findings)
│  ├─ action_queue (approvals)
│  ├─ chatbot_config (settings)
│  ├─ chat_message (history)
│  ├─ user (authentication)
│  ├─ role (authorization)
│  ├─ permission (permissions)
│  └─ user_profile (custom data)
│
└─ shopdb (vm1:5432)
   └─ Monitored tables (customer, product, order, etc.)
```

## Data Dependencies

```
Frontend → Backend:
  Login credentials → User table lookup → Password verification
  JWT token (request headers) → Token validation → User lookup → Role/permission check
  Chat message → LLMProvider → API calls (external) → Tool execution → Database query
  Config changes → Save to chatbot_config table → Load on next request

Backend → VM1:
  Orchestrator domains → PostgreSQL adapter → pg_stat_* views → Metrics extraction
  Tool execution → Database adapter → SELECT queries → Result collection → LLM response

Backend → Agent Store:
  Domain results → Save to observation table
  Tool analysis → Save to analysis table
  Key insights → Save to insight table
  Chat messages → Save to chat_message table
  User logins → Query/update user table

External APIs:
  Chatbot → Anthropic/Google/OpenAI APIs → Model responses with tool calls
  Tool calls → Database queries → Execute on vm1 → Results to LLM → Final response
```

## Security Boundaries

```
Internet ──(HTTPS)─→ nginx (arm2) ──(HTTP)─→ FastAPI (arm1) ──(TCP)─→ PostgreSQL (arm1)
                                                               ├─→ VM1 (read-only)
                                                               └─→ External LLM APIs

Authentication:
  ├─ HTTPS prevents credential interception
  ├─ Password hashing (Argon2) prevents plaintext storage
  ├─ JWT tokens prevent session replay
  ├─ 24-hour expiry forces re-authentication
  └─ Role-based access prevents unauthorized actions

Query Safety:
  ├─ SELECT-only prevents data modification
  ├─ Parameterized queries prevent SQL injection
  ├─ Query timeout (5s) prevents DoS
  ├─ Row limit (1000) prevents memory exhaustion
  └─ Monitoring user has read-only rights on vm1
```
