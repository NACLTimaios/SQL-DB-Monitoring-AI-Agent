# SQL Agent — Claude Code Context

## What this project is

A production-ready domain-focused SQL database monitoring agent running on **arm1** (OCI Free Tier, ARM64 Ampere, 2 OCPU / 12 GB RAM). It continuously monitors a PostgreSQL database on **vm1**, analyzes metrics across three independent domains, stores findings in a local PostgreSQL store, and exposes results via a FastAPI REST API on port 8084.

---

## Infrastructure

| Host | Role | Notes |
|------|------|-------|
| arm1 | Agent backend (this machine) | Runs sql_agent + agent_store PostgreSQL on port 8084 |
| arm2 | Frontend dashboard | Consumes arm1:8084 API via nginx reverse proxy |
| vm1 | Monitored database | PostgreSQL 16 instance with pg_stat_statements |
| vm2 | Load / traffic generator | Used for pgbench load tests |

**Configuration:** See `config.yaml.example` for all host/port/database placeholders. SSH key and Ansible inventory locations are environment-specific.

Existing Docker containers on arm1 (do not touch ports 8080-8083):
- `orchestrator` → 8080 (nginx placeholder)
- `tool-registry` → 8081 (nginx placeholder)
- `hitl-queue` → 8082 (nginx placeholder)
- `log-store` → 8083 (nginx placeholder)

---

## Databases

### Agent store (local on arm1)
- PostgreSQL 14, localhost:5432
- Stores: `observation`, `analysis`, `insight`, `action_queue` tables
- Initialized with: `python3 main.py init-db --config config.yaml`
- Credentials: See `config.yaml` (configure from `config.yaml.example`)

### Monitored database (vm1)
- PostgreSQL 16 instance
- Role: `pg_monitor` granted to monitoring user
- Extension: `pg_stat_statements` enabled (tracks all queries)
- Schema: Contains customer, product, and order tables
- Credentials: See `config.yaml` (configure from `config.yaml.example`)

---

## Project layout

```
sql_agent/
├── orchestrator/
│   ├── domains.py             # Domain base class + DomainRegistry
│   ├── main.py                # Orchestrator loop (SIGTERM-safe)
│   ├── aggregator.py          # Merges domain results, sets overall status
│   ├── postgres_adapter.py    # Live psycopg2 adapter for vm1 (429 lines)
│   ├── capacity_domain.py     # 60s: disk, connections, cache hit ratio
│   ├── performance_domain.py  # 300s: slow queries, table sizes
│   └── locks_domain.py        # 10s: waiting sessions, blocking chains
├── tools/
│   ├── __init__.py            # Tool abstract base class
│   ├── registry.py            # Discovers tools, topological sort on depends_on
│   ├── capacity_tools.py      # CapacityForecaster (real), StorageAdvisor (stub)
│   ├── performance_tools.py   # QueryAnalyzer (real), CostAdvisor (stub)
│   └── locks_tools.py         # LockAnalyzer (real)
├── store/
│   ├── __init__.py            # get_engine, init_db, get_session, check_db_health
│   ├── models.py              # Observation, Analysis, Insight, ActionQueue (SQLAlchemy)
│   └── repository.py          # save_*/get_* methods, activity feed, pending approvals
├── config/
│   └── loader.py              # YAML loader with structure validation
├── api/
│   └── server.py              # FastAPI, 7 endpoints, starts orchestrator on startup
├── tests/
│   ├── conftest.py            # pytest fixtures (in-memory SQLite)
│   └── test_e2e.py            # 5 integration tests
├── config.yaml                # Primary config (see below)
├── main.py                    # Click CLI: run, init-db, validate-config, status, test-domain, test-tool
└── requirements.txt           # Python dependencies
```

---

## config.yaml — current state

Key sections:

```yaml
domains:
  capacity:   { interval_seconds: 60,  monitored_db: {host: 10.0.1.189, database: shopdb} }
  performance:{ interval_seconds: 300, monitored_db: {host: 10.0.1.189, database: shopdb} }
  locks:      { interval_seconds: 10,  monitored_db: {host: 10.0.1.189, database: shopdb} }

database:     { host: localhost, port: 5432, database: agent_store, user: agent }
monitored_db: { host: 10.0.1.189, port: 5432, database: shopdb, user: monitoring }
api:          { host: 0.0.0.0, port: 8084 }   # 8080-8083 taken by Docker
```

Each domain has its own `monitored_db` block (used by domain `__init__`) plus the root `monitored_db` block (used by config loader validation).

---

## Running the agent

```bash
cd ~/sql_agent
source venv/bin/activate

# First time only
python3 main.py init-db --config config.yaml

# Start (runs on port 8084)
python3 main.py run --config config.yaml --log-level INFO

# Validate config without starting
python3 main.py validate-config --config config.yaml

# Test a single domain interactively
python3 main.py test-domain --config config.yaml --domain capacity

# Stop
pkill -f "python3 main.py run"
```

---

## API endpoints (port 8084)

| Method | Path | Description | Auth Required |
|--------|------|-------------|---|
| POST | `/api/login` | Authenticate and receive JWT token | No |
| GET | `/api/health` | System health: orchestrator running, DB connected | No |
| GET | `/api/agent-status` | Last cycle time, domains executed, overall status | **Yes** |
| GET | `/api/database/{db_id}/summary` | Connections, latency, disk, RAM | **Yes** |
| GET | `/api/insights/pending` | Insights grouped by domain (capacity/performance/locks) | **Yes** |
| GET | `/api/activity?limit=30` | Chronological feed of Observation/Analysis/Insight | **Yes** |
| POST | `/api/hitl/{action_id}/approve` | Approve/reject/escalate a queued action | **Yes** |
| GET | `/api/config/domains` | Enabled domains with intervals and tools | **Yes** |

### Authentication

Protected endpoints require JWT bearer token in `Authorization` header:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8084/api/agent-status
```

Get token via login endpoint:
```bash
curl -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"agentadmin\",\"password\":\"$AGENT_ADMIN_PASSWORD\"}"
```

Credentials:
- **Username:** `agentadmin`
- **Password:** set out-of-band (never commit it); store in a password manager / `AGENT_ADMIN_PASSWORD` env var. Hashed with argon2id at rest.
- **Token expiry:** 24 hours

---

## Key architectural decisions

- **Port 8084** (not 8080): Docker containers occupy 8080-8083 on arm1.
- **Append-only data model**: Observation → Analysis → Insight; nothing is updated or deleted.
- **Config-driven domains**: Add a domain by adding a YAML block + one Python file. No changes to orchestrator core.
- **Each domain owns its own DB connection**: `PostgreSQLAdapter` is instantiated per domain in `__init__`, not shared.
- **`pg_stat_statements`** is the source of truth for slow query data on vm1.
- **`StorageAdvisor` and `CostAdvisor`** are stubs — real logic not yet implemented.

---

## What the tools actually do (current state)

### CapacityForecaster (real)
- Assumes 200 GB total disk (OCI Free Tier estimate)
- `days_to_full = (200 - disk_size_gb) / trend_gb_per_day`
- `trend_gb_per_day` hardcoded to 0.1 until real trend tracking is implemented
- Sets `action_required=True` if `days_remaining < 30`

### QueryAnalyzer (real)
- Reads `pg_stat_statements` via adapter
- Sorts by `total_time_ms` DESC, returns top 5
- Generates per-query suggestions (seq scan, high-frequency, expensive join)
- Flags tables > 1 GB for partitioning

### LockAnalyzer (real)
- Reads `pg_stat_activity` for waiting sessions
- Reads `pg_locks` join for blocker/blocked chains
- Marks sessions waiting > 300s as critical
- Returns DBA-readable recommendations

---

## Tests

```bash
cd ~/sql_agent && source venv/bin/activate
pytest tests/test_e2e.py -v --tb=short
# Expected: 5 passed (uses in-memory SQLite, no vm1 connection needed)
```

---

## Load testing (pgbench from vm2)

Pgbench is configured to run automatically via systemd timer every 2 hours on vm2 with fluctuating load profiles (5-20 clients, varying threads and durations). This generates realistic, varying workloads for continuous monitoring.

To manually run:
```bash
ssh ubuntu@vm2-host "pgbench -h vm1-host -U monitoring -d shopdb -c 10 -j 2 -T 300"
```

Under load, the performance domain escalates to `warning` (slow queries detected) and the locks domain may show `warning` or `critical` depending on contention.

---

## Dashboard (arm2)

**Deployment:** Deployed on arm2 via nginx with HTTPS (Let's Encrypt).

**Authentication:** All pages require JWT bearer token authentication via the `/api/login` endpoint. Default credentials set in `api/auth.py` (update for production). Token is stored in localStorage and automatically included in all API requests. Session timeout: 24 hours.

**API Base:** Nginx reverse proxy forwards `/api/*` requests to arm1:8084

### Frontend stack
- React 18 + TypeScript
- Tailwind CSS 3 (custom dark theme)
- Axios with JWT interceptors
- Vite 5 build system

### Key components
- **Login.tsx** — Form-based authentication with error handling
- **App.tsx** — Auth state management, conditional rendering
- **Header.tsx** — Status badges, last cycle time, logout button
- **LocksPanel.tsx** — Shows waiting sessions with details, blocking chains
- **CapacityPanel.tsx** — Disk usage progress, connections, cache hit ratios, forecast
- **PerformancePanel.tsx** — Slow query count, top slow queries list
- **InsightsAlerts.tsx** — Collapsible domain cards with severity distribution
- **ActivityFeed.tsx** — Timeline of observations/analyses/insights

### Build & Deploy
```bash
cd ~/dashboard
npm run build          # outputs to dist/
sudo cp -r dist/* /var/www/dashboard/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Prisma AIRS Security Implementation (Completed June 2026)

### Three-Stage Scanning Pipeline

All data exchanges in the chatbot now go through Prisma AIRS scanning for security threats:

**Stage 1: User Prompt Scanning** (`orchestrator/chatbot_service.py` lines 662-678)
- Scans user input BEFORE any processing
- Detects: prompt injection, jailbreaks, prompt theft
- If blocked: LLM never called, error returned immediately

**Stage 2: Tool Output Scanning** (`orchestrator/chatbot_service.py` lines 733-758, 808-844)
- Scans database query results BEFORE LLM processes them
- Detects: credit card numbers, passwords, PII in tool results
- If blocked: LLM never receives the unscanned data, error returned
- Happens TWICE for redundancy:
  1. Immediate scan after tool execution (line 733-758)
  2. Second scan before sending to LLM agentic loop (line 808-844)

**Stage 3: Response Scanning** (`orchestrator/chatbot_service.py` lines 826-844)
- Scans LLM output BEFORE returning to user
- Detects: accidental data leakage, malicious code
- If blocked: Safe error returned instead of response

### Key Implementation Files

- **`api/prisma_airs.py`** — Core security module
  - `is_prisma_airs_enabled()` — Checks both API key AND profile are set
  - `_scan()` — Core scanning function with fail-closed error handling
  - `_safe_result()` — Returns `safe=False` on ANY error (fail-closed design)
  - `_ai_profile()` — Prefers profile_name over profile_id for reliability

- **`orchestrator/chatbot_service.py`** — Orchestrates three-stage scanning
  - Three independent `scan_response()` calls at each stage
  - Detailed [STAGE: X] labels in error messages
  - Returns `prisma_airs_user_safe` and `prisma_airs_response_safe` flags

- **`orchestrator/llm_providers.py`** — Provider-specific scanning
  - `AnthropicProvider.chat()` (lines 144-191) — Tool output scanning in agentic loop
  - After each tool execution, immediate scan before LLM sees results
  - If unsafe: returns `security_block` stop_reason without calling LLM

- **`store/chatbot_models.py`** — Database persistence
  - `ChatMessage.tool_outputs` — JSON field storing raw tool results
  - `ChatMessage.prisma_airs_user_safe` — Scan result for user input
  - `ChatMessage.prisma_airs_response_safe` — Scan result for response
  - `ChatbotConfig.prisma_airs_enabled` — Enable/disable toggle (for demo)

- **`api/server.py`** — API persistence
  - Line 900-902: Stores all three security flags in database
  - Uses actual scan results, not inferred from stop_reason

### Critical Design Decisions

1. **Fail-Closed, Not Fail-Safe**
   - If Prisma AIRS API is unavailable → ALL requests are BLOCKED
   - This prevents silent data leakage when security scanning breaks
   - Previous fail-safe approach allowed data to leak silently

2. **Profile Name Priority**
   - Changed `_ai_profile()` to prefer `PRISMA_AIRS_PROFILE_NAME` over ID
   - Profile IDs become invalid when profiles are renamed/recreated
   - Profile names are stable and human-readable

3. **Immediate Tool Output Scanning**
   - Tool results are scanned BEFORE LLM processes them
   - Prevents unscanned sensitive data from reaching the LLM
   - Second scan occurs in agentic loop for redundancy

4. **Database Schema in System Prompt**
   - Updated system prompt with exact table definitions
   - Includes critical note about using `o.id` not `o.order_id` in orders table
   - Prevents database errors and confusing agent behavior

### Frontend Changes

- **`frontend/src/components/ChatbotInfoBox.tsx`** — Removed security section
  - Removed: 🔒 Security header
  - Removed: "Prisma AIRS: ✅ Enabled" status
  - Removed: "Scanning prompts and responses" message
  - Retained: Model info, Available Tools, Admin Settings note
  - Security is configured server-side and operates transparently

- **`frontend/src/components/DashboardGrid.tsx`** — Tab navigation
  - Three tabs: Metrics, Assistant, Agent Health
  - Assistant tab shows ChatBot + ChatbotInfoBox

### Deployment Status

- **Frontend deployed to arm2** at `/var/www/dashboard/` (June 16, 2026, 20:07 UTC)
- All frontend assets updated, nginx reloaded
- Users should clear cache and refresh to see updated UI

## Chat History Privacy Implementation (Completed June 17, 2026)

### Problem
Users could see chat messages from other users, creating a **data leakage vulnerability**. Different users were viewing the same shared chat history.

### Solution
Implemented per-user chat history isolation using the authenticated username.

### Changes
- **store/chatbot_models.py:41** — Added `username` field to ChatMessage model
- **api/server.py:867** — POST /api/chatbot/chat now saves username
- **api/server.py:918** — GET /api/chatbot/history filters by current user
- **api/server.py:940** — DELETE /api/chatbot/history deletes only current user's messages

### How It Works
1. User authenticates with JWT token (contains username)
2. Message is saved with `username` field
3. When retrieving history: only show messages WHERE `username == current_user`
4. Old messages without username (from before update) are hidden

### Security Impact
**Before:** All users see all chat messages → Data leakage
**After:** Each user sees only their messages → Complete privacy isolation

### Backward Compatibility
- Old messages with `username = NULL` are hidden (not shown in history)
- No migration needed, schema handles nullable username field
- New messages automatically include username

## Portkey AI Gateway Integration (Completed June 18, 2026)

### ⚠️ Current state (supersedes the historical detail below)

Portkey is the active provider and has evolved well past the original single-shot
integration:

- **Real agentic loop** in `PortkeyProvider.chat()` (native `portkey_ai` SDK): the
  model can call tools, we execute + scan them, feed results back, and let the model
  produce the final answer. Tool results ARE sent back to the model (not formatted
  locally).
- **Conditional routing**: the client attaches `config=PORTKEY_CONFIG_ID` and tags
  each call with `metadata={"request_type": "user"|"tool"}` via `with_options()`.
  The first call is `user`; follow-ups carrying tool results are `tool`. The Portkey
  Config (built in the Portkey dashboard) decides the actual model — so the `model`
  field is just a default/fallback.
- **AIRS is now relayed by Portkey** (guardrail hook in the Config). A blocked request
  comes back as HTTP `446` / `hooks_failed`; `PortkeyProvider` reads the full body via
  `e.response.json()` (the SDK's `.body` drops `hook_results`), and
  `_portkey_guardrail_message()` turns it into a coaching message (DLP, injection,
  toxic, etc.). Returned as `stop_reason="security_block"`.
- **Our direct three-stage AIRS scanning is now LEGACY**: admin-toggled from
  *Admin → Chatbot Settings* (`prisma_airs_enabled`), **off by default** to avoid
  double-scanning. The in-loop tool scan and the orchestration scans both honor this flag.
- **Credit-card special case removed**: those queries run through the normal loop now.
- `chatbot_service` short-circuits on any provider `security_block` (returns it
  verbatim, skips our scans so the block message isn't re-scanned).

**Required env:** `PORTKEY_API_KEY` and `PORTKEY_CONFIG_ID` (both in `.env`,
gitignored — server-only). Changing the config = edit `.env`, restart the API.

**Assistant tab UI:** the top bar shows a compact **Gateway** box (Portkey only — no
model/route, since Portkey decides). Quick-action demo buttons sit to the right of the
chat (Valid Request / DLP Check / Prompt Injection / Toxic) — they insert a preset
prompt into the input without auto-sending. The per-user AIRS toggle was removed from
this tab and lives in Admin settings.

### Frontend source & deploy (IMPORTANT for future sessions)

- The **canonical frontend source is local: `/home/ubuntu/sql_agent/frontend`**. The
  copy at `arm2:~/dashboard` is **stale** (June 7, not git-tracked) — do NOT build from
  it; it would regress recent work.
- Deploy = build locally, then ship `dist/` to `arm2:/var/www/dashboard/`:
  ```bash
  cd /home/ubuntu/sql_agent/frontend && npm run build
  tar czf /tmp/dist.tgz -C dist .
  scp /tmp/dist.tgz ubuntu@10.0.2.11:/tmp/dist.tgz
  ssh ubuntu@10.0.2.11 'rm -rf /tmp/dd && mkdir -p /tmp/dd && tar xzf /tmp/dist.tgz -C /tmp/dd && \
    sudo cp -r /tmp/dd/* /var/www/dashboard/ && sudo chown -R www-data:www-data /var/www/dashboard/ && \
    rm -rf /tmp/dd /tmp/dist.tgz && sudo systemctl reload nginx'
  ```
  (Plain `scp -r dist/*` intermittently glitched in this environment; the tarball path is reliable.)
- Verify: deployed `index-*.js` hash matches local `dist/index.html`.

### Overview
Integrated Portkey AI Gateway as a new LLM provider option. Users can now route requests through Portkey's unified API gateway instead of calling LLM providers directly.

### What Is Portkey?
Portkey is an AI API gateway that:
- Routes requests to multiple LLM providers (OpenAI, Google, Anthropic, etc.)
- Provides load balancing, caching, retries, and analytics
- Requires only a single API key (PORTKEY_API_KEY)
- Uses routing syntax like `@geminiapi/gemini-2.5-flash`

### Implementation Files

**Backend Changes:**
- **orchestrator/llm_providers.py:599** — Added `PortkeyProvider` class (100+ lines)
  - Implements OpenAI-compatible chat completions
  - Uses `portkey_ai` SDK
  - Supports tool calling same as other providers
  - Added to `get_provider()` factory function

- **api/server.py:995** — Added Portkey routes to `/api/chatbot/models`
  - Routes: `@geminiapi/*`, `@openaiapi/*`, `@anthropicapi/*`
  - Users can select from dropdown in Admin Settings

- **requirements.txt** — Added `portkey-ai==0.1.0`

**Frontend Changes:**
- **frontend/src/components/admin/ChatbotSettings.tsx:142** — Added "🔀 Portkey AI Gateway" option
- **frontend/src/components/ChatbotInfoBox.tsx:100+** — Shows "🔀 Gateway" and Portkey info when selected
  - Displays: "Configured via PORTKEY_API_KEY environment variable"
  - Shows the selected route (e.g., `@geminiapi/gemini-2.5-flash`)

### How It Works

1. **User sets PORTKEY_API_KEY environment variable**
   ```bash
   export PORTKEY_API_KEY="pk_..."
   ```

2. **User selects Portkey in Admin Settings**
   - Provider: 🔀 Portkey AI Gateway
   - Route: @geminiapi/gemini-2.5-flash (or other)
   - Clicks Save

3. **Chat message flows through Portkey**
   - User message → API → PortkeyProvider
   - PortkeyProvider creates Portkey client with API key
   - Sends request to Portkey API with selected route
   - Portkey routes to actual provider (Google/OpenAI/Anthropic)
   - Response returned to user

### Configuration

**Required environment variable:**
```bash
PORTKEY_API_KEY=pk_your_portkey_key
```

**Can be set via:**
- .env file: `echo 'PORTKEY_API_KEY=pk_...' >> .env`
- Environment: `export PORTKEY_API_KEY="pk_..."`
- Systemd service: `Environment="PORTKEY_API_KEY=..."`

### Available Routes

Default routes configured (can be extended):
- `@geminiapi/gemini-2.5-flash` — Google Gemini Flash (fast + cheap)
- `@geminiapi/gemini-2.5-pro` — Google Gemini Pro
- `@openaiapi/gpt-4o` — OpenAI GPT-4o
- `@openaiapi/gpt-4-turbo` — OpenAI GPT-4 Turbo
- `@anthropicapi/claude-3-5-sonnet` — Claude Sonnet
- `@anthropicapi/claude-3-haiku` — Claude Haiku (lightweight)

### Documentation

See **[PORTKEY_SETUP.md](PORTKEY_SETUP.md)** for:
- Complete setup instructions
- Troubleshooting guide
- Advanced configuration
- Cost optimization tips
- Security considerations

### Prisma AIRS Compatibility (Verified June 18, 2026)

The three-stage Prisma AIRS scanning is done at the **orchestration level** in
`chatbot_service.py` (provider-agnostic), so it applies to Portkey the same as
other providers:

- **Stage 1 (user prompt):** `chatbot_service.py:685` — runs before any provider is called. ✅
- **Stage 2 (tool output):** `chatbot_service.py:812` — runs `if response.tool_outputs:`. ✅
- **Stage 3 (model response):** `chatbot_service.py:841` — scans `response.assistant_message`. ✅

**Critical requirement:** Each provider MUST populate `tool_outputs` in its
`ProviderResponse` for Stage 2 to fire. `PortkeyProvider.chat()` captures each
tool result into a `tool_outputs` dict (orchestrator/llm_providers.py:~654) and
passes it to `ProviderResponse(tool_outputs=...)`. Without this, the dedicated
tool-output scan is silently skipped and `tool_outputs` is not persisted for audit.

**Note on agentic loop:** PortkeyProvider does NOT feed tool output back to the
LLM for a second turn (single-shot tool execution). This means tool output never
reaches the remote model unscanned. AnthropicProvider, which DOES loop, has an
additional in-loop scan (llm_providers.py ~144-191). If PortkeyProvider is ever
upgraded to a true agentic loop, it must add the same in-loop scan.

---

## Next steps (not yet implemented)

1. **Real disk trend tracking** — store historical `disk_size_gb` observations, compute slope instead of hardcoded 0.1 GB/day
2. **StorageAdvisor** — real recommendations based on forecast
3. **CostAdvisor** — real cost/impact analysis from query profiles
4. **pgbench load test** — run from vm2, validate domain escalation
5. **HITL action execution** — wire up `action_queue` approvals to actual DBA actions
6. **Alerting** — Slack/email notifications on `critical` status
