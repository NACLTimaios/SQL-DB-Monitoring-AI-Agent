# SQL Agent — Claude Code Context

## What this project is

A production-ready domain-focused SQL database monitoring agent running on **arm1** (OCI Free Tier, ARM64 Ampere, 2 OCPU / 12 GB RAM). It continuously monitors a PostgreSQL database on **vm1**, analyzes metrics across three independent domains, stores findings in a local PostgreSQL store, and exposes results via a FastAPI REST API on port 8084.

---

## Infrastructure

| Host | Role | IP | Notes |
|------|------|----|-------|
| arm1 | Agent backend (this machine) | 10.0.2.176 | Runs sql_agent + agent_store PostgreSQL |
| arm2 | Frontend dashboard | 10.0.2.11 | Consumes arm1:8084 API |
| vm1 | Monitored database | 10.0.1.189 | PostgreSQL 16, port 5432 |
| vm2 | Load / traffic generator | 10.0.1.214 | Used for pgbench load tests |

SSH key: `~/.ssh/id_ed25519`, user `ubuntu` on all hosts.
Ansible inventory: `~/inventory/hosts.yml` and `~/agent-platform-infra/inventory/hosts.yml`.

Existing Docker containers on arm1 (do not touch ports 8080-8083):
- `orchestrator` → 8080 (nginx placeholder)
- `tool-registry` → 8081 (nginx placeholder)
- `hitl-queue` → 8082 (nginx placeholder)
- `log-store` → 8083 (nginx placeholder)

---

## Databases

### Agent store (local on arm1)
- PostgreSQL 14, `localhost:5432`
- Database: `agent_store`, user: `agent`, password: `changeme`
- Stores: `observation`, `analysis`, `insight`, `action_queue` tables
- Initialized with: `python3 main.py init-db --config config.yaml`

### Monitored database (vm1)
- PostgreSQL 16, `10.0.1.189:5432`
- Database: `shopdb`, user: `monitoring`, password: `changeme`
- Role: `pg_monitor` granted to `monitoring`
- Extension: `pg_stat_statements` enabled (tracks all queries)
- Schema: `customers` (500 rows), `products` (5 rows), `orders` (2000 rows)
- arm1 access: `10.0.2.0/24` allowed in `pg_hba.conf` (md5)

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

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health: orchestrator running, DB connected |
| GET | `/api/agent-status` | Last cycle time, domains executed, overall status |
| GET | `/api/database/{db_id}/summary` | Connections, latency, disk, RAM |
| GET | `/api/insights/pending` | Insights grouped by domain (capacity/performance/locks) |
| GET | `/api/activity?limit=30` | Chronological feed of Observation/Analysis/Insight |
| POST | `/api/hitl/{action_id}/approve` | Approve/reject/escalate a queued action |
| GET | `/api/config/domains` | Enabled domains with intervals and tools |

Quick health check: `curl -s http://localhost:8084/api/health | python3 -m json.tool`

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

```bash
# Initialize pgbench schema on shopdb
ssh -i ~/.ssh/id_ed25519 ubuntu@10.0.1.214 \
  "pgbench -i -h 10.0.1.189 -U monitoring -d shopdb"

# Run load (10 clients, 2 threads, 300 seconds)
ssh -i ~/.ssh/id_ed25519 ubuntu@10.0.1.214 \
  "pgbench -h 10.0.1.189 -U monitoring -d shopdb -c 10 -j 2 -T 300"
```

Under load, the performance domain should escalate to `warning` (slow queries detected) and the locks domain may show `warning` or `critical` depending on contention.

---

## Next steps (not yet implemented)

1. **Real disk trend tracking** — store historical `disk_size_gb` observations, compute slope instead of hardcoded 0.1 GB/day
2. **StorageAdvisor** — real recommendations based on forecast
3. **CostAdvisor** — real cost/impact analysis from query profiles
4. **pgbench load test** — run from vm2, validate domain escalation
5. **arm2 dashboard** — React/Vue frontend consuming arm1:8084 API
6. **HITL action execution** — wire up `action_queue` approvals to actual DBA actions
7. **Alerting** — Slack/email notifications on `critical` status
