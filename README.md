# SQL Agent — AI-Powered Database Monitoring

A domain-focused SQL database monitoring agent with multi-provider LLM chatbot integration. Continuously monitors PostgreSQL databases, analyzes metrics across three independent domains (capacity, performance, locks), and provides an interactive chat interface powered by Anthropic Claude, Google Gemini, or OpenAI GPT.

**⚠️ Lab/POC Setup:** This is a laboratory proof-of-concept implementation. See [Security Notice](#-lab-setup--security-notice) below before considering for production use.

## Features

### Backend Agent (arm1)
- **Domain-based monitoring** across three independent domains:
  - **Capacity:** Disk usage, connections, cache hit ratios, storage forecasting
  - **Performance:** Slow query analysis via pg_stat_statements, table statistics
  - **Locks:** Active locks, blocking sessions, lock escalation detection
- **REST API** (FastAPI) with JWT authentication on port 8084
- **Append-only data model** (Observation → Analysis → Insight)
- **Multi-provider LLM support:** Anthropic Claude, Google Gemini, OpenAI GPT-4/5
- **Database tool execution:** Query the monitored database through the chatbot
- **Safety guardrails:** Write protection, DDL prevention, query timeouts, row limits
- **Orchestrator loop** with configurable domain intervals

### Frontend Dashboard (arm2)
- **React 18 + TypeScript** with Tailwind CSS dark theme
- **Real-time chat interface** for database queries
- **Admin configuration page** for provider/model switching
- **JWT authentication** with 24-hour token expiry
- **Live status monitoring** and insights display
- **Activity feed** and timeline visualization

## ⚠️ Lab Setup / Security Notice

**This is a lab/POC setup and NOT suitable for production without significant security hardening.**

### Known Security Issues
- **Hardcoded credentials:** Default username/password (`agentadmin`/`***REMOVED-ROTATED-CREDENTIAL***`) stored in code
- **Plain text password storage:** User passwords not properly hashed with modern algorithms
- **API keys in environment:** LLM API keys loaded from `.env` (should use secrets vault)
- **No rate limiting:** API endpoints lack request rate limiting
- **Basic JWT implementation:** No token refresh mechanism or rotation
- **No audit logging:** Configuration changes and API calls not logged
- **Database credentials:** Monitored database credentials in config.yaml
- **CORS not configured:** Cross-origin requests may not be properly restricted
- **No input validation:** Limited validation on user-supplied data

### Before Production Deployment
You MUST:
1. ✅ Replace hardcoded credentials with a proper identity provider (LDAP, OAuth2, OpenID Connect)
2. ✅ Use bcrypt, Argon2, or similar for password hashing
3. ✅ Move API keys to a secrets management system (HashiCorp Vault, AWS Secrets Manager, etc.)
4. ✅ Implement comprehensive request rate limiting
5. ✅ Add token refresh and rotation mechanisms
6. ✅ Encrypt sensitive data at rest and in transit
7. ✅ Set up comprehensive audit logging and monitoring
8. ✅ Implement proper CORS and CSRF protection
9. ✅ Add extensive input validation and sanitization
10. ✅ Use TLS/HTTPS for all traffic
11. ✅ Implement role-based access control (RBAC)
12. ✅ Regular security audits and penetration testing

### Current Status
- ✅ Functional for laboratory/development testing
- ✅ Multi-provider LLM integration working
- ✅ Chatbot with database tool execution
- ❌ NOT suitable for production environments
- ❌ NOT suitable for sensitive data or regulated systems

This codebase serves as a proof-of-concept and architectural reference. Production deployments require substantial security enhancements.

## Architecture

```
User Dashboard (arm2)
    ↓
ChatBot Component / AdminPage Component
    ↓
API (arm1:8084)
    ├─ GET /api/chatbot/config
    ├─ POST /api/chatbot/config
    └─ POST /api/chatbot/chat
        ↓
    ChatbotService (provider-agnostic)
        ↓
    LLM Provider Factory
        ├─ AnthropicProvider (Claude)
        ├─ GoogleProvider (Gemini)
        └─ OpenAIProvider (GPT)
            ↓
        Database Tool Executors
            ↓
        PostgreSQL (monitored database)
```

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (monitored database)
- Node.js 16+ (for dashboard)
- LLM API key (Anthropic, Google, or OpenAI)

### 1. Backend Setup (arm1)

```bash
cd ~/sql_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env with API key
echo "GOOGLE_API_KEY=your-key-here" > .env
chmod 600 .env

# Initialize database
python3 main.py init-db --config config.yaml

# Start API
./start_api.sh
```

The API will start on `http://localhost:8084`

### 2. Frontend Setup (arm2)

```bash
cd /home/ubuntu/dashboard
npm install
npm run build
sudo cp -r dist/* /var/www/dashboard/
sudo chown -R www-data:www-data /var/www/dashboard/
sudo systemctl reload nginx
```

Access the dashboard at `https://sqlagent.dittmar.it`

### 3. Test the Chatbot

```bash
# Get JWT token
curl -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"agentadmin","password":"***REMOVED-ROTATED-CREDENTIAL***"}'

# Send a chat message
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"How many customers in the database?"}'
```

## Configuration

### config.yaml

```yaml
domains:
  capacity:
    interval_seconds: 60
    monitored_db: {host: 10.0.1.189, database: shopdb}
  performance:
    interval_seconds: 300
    monitored_db: {host: 10.0.1.189, database: shopdb}
  locks:
    interval_seconds: 10
    monitored_db: {host: 10.0.1.189, database: shopdb}

database: {host: localhost, port: 5432, database: agent_store, user: agent}
api: {host: 0.0.0.0, port: 8084}
```

### Environment Variables (.env)

Choose one LLM provider:

```bash
# Option 1: Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Google Gemini
GOOGLE_API_KEY=AIzaSy...

# Option 3: OpenAI GPT
OPENAI_API_KEY=sk-...
```

## API Endpoints

### Authentication
- `POST /api/login` — Get JWT token
  ```bash
  curl -X POST http://localhost:8084/api/login \
    -d '{"username":"agentadmin","password":"***REMOVED-ROTATED-CREDENTIAL***"}'
  ```

### Health
- `GET /api/health` — System health check (no auth)

### Agent Status
- `GET /api/agent-status` — Orchestrator status, last cycle time
- `GET /api/database/{db_id}/summary` — Connections, latency, disk, RAM
- `GET /api/insights/pending` — Pending insights by domain
- `GET /api/activity?limit=30` — Activity feed

### Chatbot
- `GET /api/chatbot/config` — Current configuration
- `POST /api/chatbot/config` — Update configuration (admin)
- `POST /api/chatbot/chat` — Send message to chatbot
- `GET /api/chatbot/history?limit=50` — Chat message history
- `GET /api/chatbot/tools` — List available database tools
- `GET /api/chatbot/guardrails` — Safety constraints

All endpoints except `/api/login` and `/api/health` require JWT bearer token:
```bash
-H "Authorization: Bearer <token>"
```

## Chatbot Features

### Available Database Tools
1. **query_database** — Execute SELECT queries
2. **get_metrics** — Database metrics (connections, disk, cache hit ratio)
3. **get_slow_queries** — Top slow queries from pg_stat_statements
4. **get_table_stats** — Table sizes and statistics
5. **check_locks** — Active locks and blocking sessions

### Safety Guardrails
- **Write protection** — Only SELECT queries allowed (configurable)
- **DDL prevention** — No ALTER/CREATE/DROP statements
- **Query timeout** — 5 seconds default (configurable 1-60s)
- **Row limit** — 1000 rows default (configurable 100-10000)

### Example Conversations
```
User: "How many customers are in the database?"
Chatbot: [Executes query_database tool with SELECT COUNT(*) FROM customers]
Response: "There are 500 customers in the database."

User: "Show me the slowest queries"
Chatbot: [Executes get_slow_queries tool]
Response: [Lists top 5 slow queries with execution times and recommendations]

User: "Are there any active locks?"
Chatbot: [Executes check_locks tool]
Response: [Shows blocking chains and waiting sessions]
```

## Switching LLM Providers

### Via Admin Page (Easiest)
1. Login to dashboard
2. Click "Admin Settings"
3. Select provider from dropdown
4. Change model name if desired
5. Click "Save Configuration"

### Via API
```bash
curl -X POST http://localhost:8084/api/chatbot/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_provider": "google",
    "llm_model": "gemini-2.5-flash"
  }'
```

### Via Database
```sql
UPDATE chatbot_config SET 
  llm_provider = 'google',
  llm_model = 'gemini-2.5-flash'
WHERE id = 1;
```

## Supported Models

| Provider | Model | Status |
|----------|-------|--------|
| **Anthropic** | claude-3-5-sonnet-20241022 | ✅ Supported |
| **Google** | gemini-2.5-flash | ✅ Recommended |
| | gemini-2.5-pro | ✅ Supported |
| | gemini-2.0-flash | ✅ Supported |
| **OpenAI** | gpt-4-turbo | ✅ Supported |
| | gpt-4o | ✅ Supported |

## Deployment

### Deploy to arm2 Dashboard
```bash
# Copy components
scp frontend/src/components/ChatBot.tsx arm2:/path/to/dashboard/src/components/
scp frontend/src/pages/AdminPage.tsx arm2:/path/to/dashboard/src/pages/

# Update App.tsx with imports and routes
# Rebuild and deploy
cd /path/to/dashboard
npm run build
sudo cp -r dist/* /var/www/dashboard/
sudo systemctl reload nginx
```

See [DEPLOY_TO_ARM2.md](DEPLOY_TO_ARM2.md) for detailed instructions.

## Project Structure

```
sql_agent/
├── orchestrator/
│   ├── llm_providers.py       # Multi-provider LLM abstraction
│   ├── chatbot_service.py     # Chatbot logic (provider-agnostic)
│   ├── domains.py             # Domain base class
│   ├── capacity_domain.py      # Capacity monitoring
│   ├── performance_domain.py   # Query performance monitoring
│   └── locks_domain.py         # Lock detection
├── tools/
│   ├── registry.py            # Tool discovery and loading
│   └── {domain}_tools.py       # Domain-specific tools
├── store/
│   ├── models.py              # SQLAlchemy ORM models
│   ├── chatbot_models.py       # Chatbot config and chat history
│   └── repository.py          # Data access layer
├── api/
│   └── server.py              # FastAPI endpoints
├── frontend/
│   ├── src/components/
│   │   └── ChatBot.tsx         # Chat interface component
│   └── src/pages/
│       └── AdminPage.tsx       # Admin configuration page
├── config.yaml                # Monitoring configuration
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
└── .env                       # API keys (gitignored)
```

## CLI Commands

```bash
# Initialize database
python3 main.py init-db --config config.yaml

# Start agent and API
python3 main.py run --config config.yaml

# Validate configuration
python3 main.py validate-config --config config.yaml

# Check agent status
python3 main.py status --config config.yaml

# Test a single domain
python3 main.py test-domain --config config.yaml --domain capacity

# Test a single tool
python3 main.py test-tool --config config.yaml --tool capacity_forecaster
```

## Running Tests

```bash
source venv/bin/activate
pytest tests/test_e2e.py -v
```

Expected: 5 integration tests passing (uses in-memory SQLite)

## Troubleshooting

### "API key not configured"
- Set the appropriate API key environment variable
- Verify it's exported before starting the API: `echo $GOOGLE_API_KEY`
- Restart the API with `./start_api.sh`

### "Cannot GET /api/*" 404 errors
- Verify nginx is proxying `/api/` to arm1:8084
- Check `/etc/nginx/sites-available/dashboard` configuration
- Reload nginx: `sudo systemctl reload nginx`

### Chat messages not loading
- Verify JWT token is valid and not expired
- Check browser console for CORS errors
- Ensure API is running: `curl http://localhost:8084/api/health`

### Configuration not saving
- Check network tab in browser dev tools
- Verify API key is set on backend
- Check backend logs for errors: `tail /tmp/api.log`

## Security Notes

✅ **Protected:**
- API keys in `.env` (gitignored, permissions 600)
- JWT tokens with 24-hour expiry
- Database queries limited to SELECT-only by default
- SQL injection protection through parameterized queries

⚠️ **Consider for Production:**
- Encrypt API keys at rest
- Use stronger authentication (LDAP, OAuth)
- Enable HTTPS/TLS for all traffic
- Implement request rate limiting
- Add audit logging for configuration changes
- Restrict database user to read-only access

## Performance Notes

- **Capacity domain:** 60-second intervals (adjustable)
- **Performance domain:** 300-second intervals (adjustable)
- **Locks domain:** 10-second intervals (adjustable)
- **Chat response time:** 2-10 seconds depending on LLM and query complexity
- **Query timeout:** 5 seconds default (configurable 1-60s)

## Documentation

- [CHATBOT_IMPLEMENTATION.md](CHATBOT_IMPLEMENTATION.md) — Technical implementation details
- [LLM_PROVIDER_SETUP.md](LLM_PROVIDER_SETUP.md) — Setup guides for all 3 providers
- [GOOGLE_GEMINI_SETUP.md](GOOGLE_GEMINI_SETUP.md) — Google Gemini specific setup
- [DEPLOY_TO_ARM2.md](DEPLOY_TO_ARM2.md) — Frontend deployment guide
- [CLAUDE.md](CLAUDE.md) — Complete project context for Claude AI

## License

Proprietary - SQL Agent Monitoring System

## Support

For issues or questions, check the documentation files listed above or review the API logs at `/tmp/api.log`.
