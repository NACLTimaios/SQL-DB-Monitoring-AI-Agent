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
- **Admin Settings page** (admin-only access):
  - Chatbot provider and model configuration
  - User management (create, edit, delete users)
  - Role-based access control
- **JWT authentication** with 24-hour token expiry
- **Persistent user management** with password hashing (Argon2)
- **Live status monitoring** and insights display
- **Activity feed** and timeline visualization
- **Role-based UI** - Non-admin users see access denied message with instructions

## ⚠️ Lab Setup / Security Notice

**This is a lab/POC setup and NOT suitable for production without significant security hardening.**

### Known Security Issues
- **API keys in environment:** LLM API keys loaded from `.env` (should use secrets vault)
- **No rate limiting:** API endpoints lack request rate limiting
- **Basic JWT implementation:** No token refresh mechanism or rotation
- **No audit logging:** Configuration changes and API calls not logged
- **Database credentials:** Monitored database credentials in config.yaml
- **CORS not configured:** Cross-origin requests may not be properly restricted
- **No input validation:** Limited validation on user-supplied data

### Before Production Deployment
You MUST:
1. ⚠️ Replace hardcoded credentials with a proper identity provider (LDAP, OAuth2, OpenID Connect)
2. ✅ Use bcrypt, Argon2, or similar for password hashing (IMPLEMENTED: Argon2)
3. ⚠️ Move API keys to a secrets management system (HashiCorp Vault, AWS Secrets Manager, etc.)
4. ❌ Implement comprehensive request rate limiting
5. ❌ Add token refresh and rotation mechanisms
6. ❌ Encrypt sensitive data at rest and in transit
7. ❌ Set up comprehensive audit logging and monitoring
8. ❌ Implement proper CORS and CSRF protection
9. ❌ Add extensive input validation and sanitization
10. ✅ Use TLS/HTTPS for all traffic
11. ✅ Implement role-based access control (RBAC) (IMPLEMENTED: admin/dashboard roles)
12. ✅ Persistent user authentication (IMPLEMENTED: PostgreSQL-backed)
13. ❌ Regular security audits and penetration testing

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
# Get JWT token (default admin user - MUST be changed on first login!)
curl -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme"}'

# Send a chat message
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"How many customers in the database?"}'
```

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
Tokens are obtained from `/api/login` and expire after 24 hours.

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
