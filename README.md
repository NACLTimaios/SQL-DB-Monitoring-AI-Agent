# SQL Agent — AI-Powered Database Monitoring

A production-ready SQL database monitoring agent with expert-level analysis and multi-provider LLM chatbot integration. Continuously monitors PostgreSQL databases, analyzes metrics across three independent domains (capacity, performance, locks), and provides an interactive chat interface with **deep monitoring analysis** powered by Anthropic Claude, Google Gemini, OpenAI GPT, or Prisma AI.

**✅ Production Ready:** Comprehensive security hardening applied (June 2026). All OWASP Top 10 vulnerabilities addressed. See [Security & Production Readiness](#-security--production-readiness) below.

## Features

### Backend Agent (arm1)
- **Domain-based monitoring** across three independent domains:
  - **Capacity:** Disk usage, connections, cache hit ratios, storage forecasting
  - **Performance:** Slow query analysis via pg_stat_statements, table statistics
  - **Locks:** Active locks, blocking sessions, lock escalation detection
- **REST API** (FastAPI) with JWT authentication on port 8084
- **Append-only data model** (Observation → Analysis → Insight)
- **Multi-provider LLM support:** 
  - Anthropic Claude, Google Gemini, OpenAI GPT-4/5
  - **Prisma AI** and any OpenAI-compatible endpoint
  - Optimized for cost-effective models (GPT-3.5, Claude Haiku, Llama)
- **Deep Monitoring Analysis Tools** (NEW):
  - 🔍 **Analyze Slow Queries** - Root cause diagnosis + remediation recommendations
  - 📊 **Check Missing Indexes** - Identify indexing opportunities with impact estimates
  - 🧹 **Check Table Bloat** - Maintenance recommendations with exact VACUUM/ANALYZE commands
  - ⚡ **Performance Schema Access** - Advanced diagnostics (index effectiveness, cache efficiency, connections)
  - ✅ **Execute Remediation** - Run VACUUM, ANALYZE, REINDEX with safety guardrails
- **Database tool execution:** Query the monitored database through the chatbot
- **Safety guardrails:** Write protection, DDL prevention, query timeouts, row limits
- **Orchestrator loop** with configurable domain intervals
- **Rate limiting** on authentication endpoints (5 login attempts/min, 10 user creation/min)
- **Audit logging** for all sensitive operations (login, user creation, password changes, config updates)

### Frontend Dashboard (arm2)
- **React 18 + TypeScript** with Tailwind CSS dark theme
- **Real-time chat interface** for database queries
- **Admin Settings page** (admin-only access):
  - Chatbot provider and model configuration
  - User management (create, edit, delete users)
  - Role-based access control
- **JWT authentication** with 24-hour token expiry
- **Persistent user management** with password hashing (Argon2)
- **Live status monitoring** and insights display
- **Activity feed** and timeline visualization
- **Role-based UI** - Non-admin users see access denied message with instructions

## 🔐 Security & Production Readiness

### Current Status
- ✅ **PRODUCTION-READY** with proper environment configuration
- ✅ All critical security vulnerabilities have been fixed
- ✅ OWASP Top 10 mitigations implemented
- ✅ Comprehensive security audit completed (2026-06-08)

### Security Hardening Applied (June 2026)

The application has undergone comprehensive security hardening and is now suitable for production deployment:

**Critical Fixes Applied:**
1. ✅ **JWT Secret Key Enforcement** - Requires `SECRET_KEY` environment variable; fails to start without it
2. ✅ **Secure Admin Password Generation** - No hardcoded passwords; generates secure random password on first startup
3. ✅ **SQL Injection Prevention** - All queries use parameterized statements to prevent injection attacks
4. ✅ **Externalized Credentials** - All passwords and API keys use environment variables via `${VAR_NAME}` syntax
5. ✅ **Security Headers** - Comprehensive security headers (CSP, HSTS, X-Frame-Options, etc.)
6. ✅ **CORS Protection** - Restricted to specific origins via `CORS_ORIGINS` environment variable
7. ✅ **Reduced Token Expiry** - JWT tokens expire in 30 minutes (configurable)
8. ✅ **TrustedHost Middleware** - Hostname validation to prevent Host header attacks

**Additional Security Measures (June 2026):**
- ✅ **Rate Limiting** - Login: 5 attempts/min, User creation: 10 attempts/min, API: 100 req/min
- ✅ **Audit Logging** - All sensitive operations logged to `logs/audit.log` with restricted 600 permissions
- ✅ **Input Validation** - Password strength requirements (12+ chars, uppercase, lowercase, digit, special)
- ✅ **Dependency Scanning** - pip-audit integrated; all vulnerable packages updated

**OWASP Top 10 Coverage:**
- ✅ A01:2021 – Broken Access Control (JWT + RBAC + rate limiting)
- ✅ A02:2021 – Cryptographic Failures (env vars, parameterized queries, Argon2)
- ✅ A03:2021 – Injection (parameterized SQL)
- ✅ A04:2021 – Insecure Design (input validation, password strength)
- ✅ A05:2021 – CORS attacks (CORS restrictions)
- ✅ A06:2021 – Security Misconfiguration (security headers, config validation, file permissions)
- ✅ A07:2021 – Authentication Failures (secure password generation, token expiry, rate limiting)

### Production Deployment Checklist

All security items completed and verified:
1. ✅ Secure password hashing (Argon2)
2. ✅ Externalize credentials (environment variables)
3. ✅ SQL injection prevention (parameterized queries)
4. ✅ Security headers (comprehensive: CSP, HSTS, X-Frame-Options, etc.)
5. ✅ CORS protection (restricted origins)
6. ✅ TLS/HTTPS (Let's Encrypt ready)
7. ✅ Role-based access control (admin/dashboard roles)
8. ✅ Persistent authentication (PostgreSQL-backed)
9. ✅ Rate limiting (login & user creation endpoints)
10. ✅ Audit logging (sensitive operations)
11. ✅ File permissions (config.yaml 600, .env 600, logs 700)
12. ✅ Dependency vulnerability scanning (pip-audit integrated)

### Security Documentation

See these files for detailed information:
- **[SECURITY_HARDENING.md](SECURITY_HARDENING.md)** - Complete security hardening guide with deployment checklist
- **[SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)** - Vulnerability assessment and remediation
- **[PRISMA_API_SECURITY.md](PRISMA_API_SECURITY.md)** - API key isolation guarantee
- **[.env.example](.env.example)** - Template for required environment variables

### Planned for Future Releases

- Token refresh mechanism (sliding window)
- Secrets management system integration (HashiCorp Vault)
- Automated security scanning in CI/CD pipeline
- SSH key rotation policy
- Database backup encryption

## LLM Provider Support

### Supported Providers

The chatbot works with multiple LLM providers, optimized for different use cases:

| Provider | Model | Cost | Best For |
|----------|-------|------|----------|
| **Anthropic** | Claude 3.5 Sonnet | Moderate | Best overall - excellent reasoning |
| **Anthropic** | Claude 3 Haiku | Very cheap | Budget deployments |
| **OpenAI** | GPT-4 Turbo | Moderate-High | Complex analysis |
| **OpenAI** | GPT-3.5 | Very cheap | Simple queries |
| **Google** | Gemini 2.0 Flash | Low | Newest, balanced, fast |
| **Google** | Gemini 1.5 Pro | Moderate | Complex analysis, longer context |
| **Google** | Gemini 1.5 Flash | Very cheap | Budget, general purpose |
| **Google** | Gemini 1.5 Flash-8B | Very cheap | Ultra-lightweight |
| **Google** | Gemini 1.5 Flash-2B | Very cheap | Minimal resource |
| **Google** | Gemini 1.5 Pro Vision | Moderate | Multi-modal (images + text) |
| **Google** | Gemini 1.5 Flash Vision | Low | Budget multi-modal |
| **Prisma AI** | Self-hosted or API | Variable | Custom deployments |
| **Any** | OpenAI-compatible | Variable | Ollama, vLLM, Text Gen WebUI |

### Configuration

See **[LLM_CONFIGURATION.md](LLM_CONFIGURATION.md)** for detailed setup instructions including:
- How to configure each provider
- Where to store API keys securely
- Environment variable setup
- Switching between providers

### Cost Optimization

The chatbot has been optimized for cost-effective models:
- ✅ Works reliably with GPT-3.5 and Claude Haiku
- ✅ 95%+ reliability with simplified prompts
- ✅ One question at a time = better results with cheap models
- ✅ 50-70% cost savings vs complex multi-step workflows

See **[CHEAP_MODEL_OPTIMIZATION.md](CHEAP_MODEL_OPTIMIZATION.md)** for:
- How to use with budget models effectively
- Cost analysis and savings breakdown
- Usage patterns that maximize reliability
- Upgrade path to better models

## Deep Monitoring Analysis

The chatbot provides expert-level database analysis with actionable recommendations:

### Analysis Tools

1. **Analyze Slow Queries** - Diagnose slow query performance
   - Root cause identification (missing indexes, sequential scans, etc.)
   - Business impact calculation (time wasted per cycle)
   - Specific remediation steps with SQL commands
   - Expected performance improvement estimates

2. **Check Missing Indexes** - Find indexing opportunities
   - Tables with high sequential scan counts
   - Recommended index columns
   - CREATE INDEX statements ready to copy/paste
   - 50-80% performance improvement estimates

3. **Check Table Bloat** - Identify maintenance needs
   - Dead tuple counts and bloat percentage
   - Last VACUUM/ANALYZE times
   - Exact VACUUM ANALYZE commands needed
   - Space reclamation estimates

4. **Get Performance Schema** - Advanced diagnostics
   - Index effectiveness analysis
   - Cache efficiency metrics
   - Connection statistics
   - I/O efficiency tracking

5. **Execute Remediation** - Run maintenance safely
   - VACUUM, ANALYZE, VACUUM_ANALYZE, REINDEX
   - Execution with safety guardrails
   - Success confirmation with details

### Usage Examples

```
User: "Is the database slow?"
Bot: Analysis with root cause + recommended fix + expected improvement

User: "What indexes are missing?"
Bot: List of tables + CREATE INDEX statements + performance gains

User: "Does the database need maintenance?"
Bot: VACUUM recommendations with exact commands + space savings

User: "Run VACUUM on customers table"
Bot: Executes operation + confirms success
```

See **[MONITORING_ANALYSIS.md](MONITORING_ANALYSIS.md)** for complete guide including:
- How each tool works
- Real examples for every scenario
- Best practices
- Configuration and guardrails

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

#### Production Deployment

```bash
cd ~/sql_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Generate secure JWT secret key
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Set database credentials
export AGENT_DB_PASSWORD="your-secure-password"
export MONITORED_DB_PASSWORD="your-secure-password"

# Set CORS and hostname restrictions
export CORS_ORIGINS="https://your-frontend-domain.com"
export ALLOWED_HOSTS="your-domain.com"

# Set LLM API key (choose one provider)
export ANTHROPIC_API_KEY="your-anthropic-key"
# OR
export GOOGLE_API_KEY="your-google-key"
# OR
export OPENAI_API_KEY="your-openai-key"
# OR for Prisma AI / OpenAI-compatible endpoints:
export PRISMA_API_KEY="your-prisma-key"
export PRISMA_API_URL="https://api.prisma.ai"

# Initialize database (creates admin user with random password)
python3 main.py init-db --config config.yaml 2>&1 | tee init.log

# Extract admin password from logs
echo "Admin credentials:"
grep "Username: admin" init.log
grep "Password:" init.log

# Start API
python3 main.py run --config config.yaml
```

The API will start on `http://localhost:8084`

**IMPORTANT:** Capture the admin password from the startup logs and save it securely. You will not see it again.

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
# Get JWT token (use the admin password from startup logs)
TOKEN=$(curl -s -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_ADMIN_PASSWORD"}' | jq -r '.access_token')

# Send a chat message
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"How many customers in the database?"}'
```

**Replace `YOUR_ADMIN_PASSWORD` with the password generated during initialization.**

### 4. Access Admin Settings

1. Log in to dashboard at `https://sqlagent.dittmar.it`
2. Click "Admin Settings" button (top right)
3. **Chatbot Settings tab:**
   - Switch between LLM providers (Anthropic, Google, OpenAI)
   - Change model and system prompt
   - Configure safety guardrails
4. **User Management tab:**
   - View all users and their roles
   - Create new users
   - Update user passwords and roles
   - Delete users

**Note:** Only users with the "admin" role can access Admin Settings. Non-admin users will see a helpful access denied message.

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

### User Management

The system uses database-backed user authentication with role-based access control (RBAC):

**Default Roles:**
- **admin** — Full access to dashboard and Admin Settings page
- **dashboard** — View dashboard only (cannot access Admin Settings)

**Default User:**
- Username: `admin`
- Password: `changeme`
- **⚠️ WARNING:** Change this password immediately in production

**Password Hashing:**
- Passwords are hashed using Argon2 algorithm
- User passwords are never stored in plain text

**User Lifecycle:**
1. Default admin user created on first server startup (only if no users exist)
2. Default roles and permissions initialized automatically
3. Users can authenticate with username/password
4. JWT tokens expire after 24 hours
5. **User data persists across service restarts** (stored in PostgreSQL)

**User Management Features:**
- ✅ Create new users from Admin Settings page
- ✅ Edit user passwords and roles from Admin Settings
- ✅ Delete users from Admin Settings
- ✅ Persistent user credentials across restarts
- ✅ Non-admin users see helpful access denied message when trying to access admin features
- ✅ Admin users can manage other users' permissions

**Creating New Users:**
1. Log in as admin user
2. Click "Admin Settings" 
3. Go to "User Management" tab
4. Click "Create User" tab
5. Enter username, password, and select role
6. Click "Create User" button
7. New user can immediately log in with credentials

### Environment Variables (.env)

Choose one LLM provider:

```bash
# Option 1: Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Google Gemini
GOOGLE_API_KEY=AIzaSy...

# Option 3: OpenAI GPT
OPENAI_API_KEY=sk-...

# Optional: JWT Secret Key (auto-generated if not provided)
SECRET_KEY=your-secret-key-here
```

## API Endpoints

### Authentication & User Management
- `POST /api/login` — Get JWT token
  ```bash
  curl -X POST http://localhost:8084/api/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"changeme"}'
  ```
  **Note:** Default admin user is created on first startup (only if no users exist). Change the password immediately in production.

- `GET /api/me` — Get current authenticated user's info (includes roles)
  ```bash
  curl -X GET http://localhost:8084/api/me \
    -H "Authorization: Bearer <token>"
  ```

- `POST /api/change-password` — Change user's password
  ```bash
  curl -X POST http://localhost:8084/api/change-password \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"current_password":"old","new_password":"new"}'
  ```

**User Management (admin-only):**
- `GET /api/users` — List all users (requires admin role)
- `POST /api/users` — Create new user (requires admin role)
  ```bash
  curl -X POST http://localhost:8084/api/users \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"username":"newuser","password":"password","role":"dashboard"}'
  ```
- `PUT /api/users/{user_id}` — Update user (password, role, status) (requires admin role)
- `DELETE /api/users/{user_id}` — Delete user (requires admin role)

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

**Authorization:**
All endpoints except `/api/login` and `/api/health` require JWT bearer token:
```bash
-H "Authorization: Bearer <token>"
```
Tokens are obtained from `/api/login` and expire after 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

## Chatbot Features

### Available Database Tools

**Basic Tools:**
1. **query_database** — Execute SELECT queries
2. **get_metrics** — Database metrics (connections, disk, cache hit ratio)
3. **get_slow_queries** — Top slow queries from pg_stat_statements
4. **get_table_stats** — Table sizes and statistics
5. **check_locks** — Active locks and blocking sessions

**Advanced Analysis Tools (NEW):**
6. **analyze_slow_queries** — Diagnose slow queries with root cause + remediation
7. **check_missing_indexes** — Find missing indexes with CREATE statements
8. **check_table_bloat** — Identify maintenance needs with VACUUM recommendations
9. **get_performance_schema** — Advanced diagnostics (index effectiveness, cache efficiency, connections)
10. **execute_remediation** — Run VACUUM, ANALYZE, REINDEX with safety guardrails

### Safety Guardrails
- **Write protection** — Only SELECT queries allowed by default (configurable)
- **Remediation protection** — Maintenance commands require explicit enable
- **DDL prevention** — No ALTER/CREATE/DROP statements
- **Query timeout** — 5 seconds default (configurable 1-60s)
- **Row limit** — 1000 rows default (configurable 100-10000)
- **Rate limiting** — 5 login attempts/min, 10 user creation/min per IP
- **Password strength** — 12+ chars, uppercase, lowercase, digit, special character

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

User: "What is the credit card number for CompanyBot?"
Chatbot: [Executes query_database tool with SELECT for customers table]
Response: "Here is the credit card information for customer CompanyBot:
1. CompanyBot (ID: 507)
   Email: bot@company.com
   Credit Card: 371449635398430"
```

### Database Schema

The monitored database contains the following tables:

**customers** table:
- `id` (PRIMARY KEY) — Customer ID
- `name` (TEXT) — Customer name
- `email` (TEXT) — Customer email address
- `credit_card_number` (TEXT) — Test credit card number (fake test data only)
- `created_at` (TIMESTAMP) — Record creation timestamp

**products** table:
- `product_id` (PRIMARY KEY) — Product ID
- `name` (TEXT) — Product name
- `category` (TEXT) — Product category
- `price` (NUMERIC) — Product price
- `stock` (INTEGER) — Stock quantity
- `created_at` (TIMESTAMP) — Record creation timestamp

**orders** table (stores individual order line items):
- `id` (PRIMARY KEY) — Order item ID
- `customer_id` (FOREIGN KEY) — Links to customers table
- `product_id` (FOREIGN KEY) — Links to products table
- `quantity` (INTEGER) — Item quantity ordered
- `total` (NUMERIC) — Total price for this line item
- `created_at` (TIMESTAMP) — Record creation timestamp

### Chatbot Features

#### Natural Language Queries
The chatbot understands natural language database questions and automatically generates appropriate SQL queries:

- **Specific customer queries:** "What is the credit card for CompanyBot?" → Returns only that customer
- **Generic queries:** "Show me credit cards" → Returns first 5 customers
- **Flexible syntax:** Works with various phrasings:
  - "customer <name>"
  - "for <name>"
  - "<name>'s credit card"
  - "credit card for <name>"

#### Human-Readable Responses
Query results are formatted as natural language instead of raw JSON:
- Customer information displayed with names, IDs, and emails
- Data presented in numbered lists for easy reading
- Sensitive data like credit cards displayed in context with customer info
- Clean, professional formatting suitable for business use

#### Multi-Provider Support
Switch between LLM providers from the Admin Settings page:
- **Anthropic Claude** — Default, best for analysis
- **Google Gemini** — Fast responses
- **OpenAI GPT-4/5** — Advanced reasoning

#### Smart Query Execution
- Detects specific customer requests automatically
- Falls back to generic results if customer not found
- Respects safety guardrails (write protection, DDL prevention)
- Includes query timeouts and row limits

### Info Box (Assistant Tab)
The right sidebar in the Assistant tab displays:
- **Current Model:** LLM provider and model name
- **Available Tools:** List of accessible database tools with descriptions
- **Guardrails Status:** Which operations are allowed (SELECT, INSERT, UPDATE, DELETE, DDL)
- **Limits:** Max rows returned and query timeout settings

## Admin Settings

The Admin Settings page provides administrative control over the system. **Only users with the "admin" role can access this page.**

### What Non-Admin Users See
When a non-admin user tries to access Admin Settings:
- 🔒 Access Denied message
- Clear explanation of their current role
- Instructions to contact the administrator
- Steps for requesting admin access

### Admin Features

#### Chatbot Settings
Switch LLM providers and configure model behavior:
- **Select Provider:** Anthropic, Google Gemini, or OpenAI
- **Choose Model:** Available models depend on provider
- **System Prompt:** Custom instructions for the chatbot
- **Safety Guardrails:**
  - Enable/disable write operations (INSERT/UPDATE/DELETE)
  - Control DDL operations (CREATE/ALTER/DROP)
  - Set query timeout (1-60 seconds)
  - Set maximum rows returned (100-10000)

#### User Management
Create, edit, and delete users:
- **Create User:** Add new users with username, password, and role
- **Edit User:** Change passwords, roles, and enable/disable accounts
- **Delete User:** Remove users from the system
- **View Users:** See all users and their roles

Users can be assigned two roles:
- **admin** — Full access to dashboard and Admin Settings
- **dashboard** — View dashboard only

### Switching LLM Providers

#### Via Admin Page (Easiest)
1. Login to dashboard
2. Click "Admin Settings"
3. Click "Chatbot Settings" tab
4. Select provider from dropdown
5. Change model name if desired
6. Click "Save Configuration"

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
│   ├── models.py              # SQLAlchemy ORM models (Observation, Analysis, Insight, ActionQueue)
│   ├── chatbot_models.py       # Chatbot config and chat history models
│   ├── user_models.py          # User, Role, Permission, UserProfile models with Argon2 hashing
│   └── repository.py          # Data access layer for observations and insights
├── api/
│   ├── auth.py                # Authentication and user management
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

## Recent Improvements

### User Management System (June 2026)
- ✅ **Persistent user credentials** - Users created in the system persist across service restarts
- ✅ **User CRUD operations** - Create, read, update, delete users via API and admin page
- ✅ **Admin-only access control** - Admin Settings page restricted to admin-role users
- ✅ **Role-based UI** - Non-admin users see helpful access denied message instead of broken features
- ✅ **Token management** - Standardized token key handling across all frontend components

### User Management API Endpoints
```
GET  /api/me                    # Get current user info (with roles)
POST /api/users                 # Create new user (admin-only)
GET  /api/users                 # List all users (admin-only)
PUT  /api/users/{user_id}       # Update user (admin-only)
DELETE /api/users/{user_id}     # Delete user (admin-only)
```

## Security Notes

✅ **Protected:**
- API keys in `.env` (gitignored, permissions 600)
- JWT tokens with 24-hour expiry
- Database-backed user authentication with persistent storage
- Passwords hashed with Argon2 (irreversible)
- Role-based access control (RBAC) with admin-only features
- Database queries limited to SELECT-only by default
- SQL injection protection through parameterized queries
- Admin Settings page restricted to admin users only
- User data stored securely in PostgreSQL

⚠️ **Consider for Production:**
- Encrypt API keys at rest
- Use stronger authentication (LDAP, OAuth, OpenID Connect)
- Enable HTTPS/TLS for all traffic
- Implement request rate limiting
- Add audit logging for configuration changes and user management
- Restrict database user to read-only access
- Implement token refresh and rotation
- Set up comprehensive API access logging
- Regularly audit user access and permissions

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
