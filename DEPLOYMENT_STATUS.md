# Deployment Status (June 16, 2026)

## Current Deployment State

### Backend (arm1)
- **Status:** Running
- **Location:** /home/ubuntu/sql_agent/
- **Service:** Python FastAPI on port 8084
- **Database:** PostgreSQL (agent_store on arm1, monitored DB on vm1)
- **Last Updated:** June 2026
- **Configuration:** config.yaml with all domains enabled

**Key Environment Variables (Required):**
```bash
SECRET_KEY=<jwt-secret>                    # Required for authentication
ANTHROPIC_API_KEY=<api-key>                # Or GOOGLE_API_KEY or OPENAI_API_KEY
PRISMA_AIRS_API_KEY=<api-key>              # For security scanning
PRISMA_AIRS_PROFILE_NAME=Default           # AI Security profile name
```

**Start Backend:**
```bash
source venv/bin/activate
python3 main.py run --config config.yaml
```

### Frontend (arm2)
- **Status:** Deployed to /var/www/dashboard/
- **URL:** https://sqlagent.dittmar.it
- **Last Deployed:** June 16, 2026, 20:07 UTC
- **Build Date:** June 16, 2026, 20:05 UTC
- **Nginx:** Configured and reloaded successfully
- **Files:** dist/* with index.html and assets/

**Deployment Command:**
```bash
cd /home/ubuntu/sql_agent/frontend
npm run build
ssh ubuntu@10.0.2.11 "mkdir -p /tmp/dashboard-deploy"
scp -r dist/* ubuntu@10.0.2.11:/tmp/dashboard-deploy/
ssh ubuntu@10.0.2.11 "sudo cp -r /tmp/dashboard-deploy/* /var/www/dashboard/ && \
  sudo chown -R www-data:www-data /var/www/dashboard/ && \
  rm -rf /tmp/dashboard-deploy && \
  sudo nginx -t && sudo systemctl reload nginx"
```

## Recent Changes

### Prisma AIRS Security (June 2026)
- ✅ Three-stage scanning implemented: user prompts, tool outputs, LLM responses
- ✅ Fail-closed design (blocks on API unavailability)
- ✅ Profile name preferred over profile ID
- ✅ Three independent scan points for redundancy
- ✅ All scan results stored in database

**Files Modified:**
- api/prisma_airs.py — Core scanning module
- orchestrator/chatbot_service.py — Orchestration and logging
- orchestrator/llm_providers.py — Provider-specific scanning
- store/chatbot_models.py — Database schema with security flags
- api/server.py — Endpoint persistence

### Database Schema (June 2026)
- ✅ System prompt updated with exact table definitions
- ✅ Critical notes about column names (orders.id NOT orders.order_id)
- ✅ Clarification that no order_items table exists

**Tables:**
- customers (id, name, email, credit_card_number, created_at)
- products (product_id, name, category, price, stock, created_at)
- orders (id, customer_id, product_id, quantity, total, created_at)

### Frontend UI (June 16, 2026)
- ✅ Assistant Info Box security section removed
- ✅ Displays: Model, Tools, Admin Settings note
- ✅ Security scanning operates transparently (no UI indicator)
- ✅ Clean, simplified UI without security status display

## Health Checks

### Backend Health
```bash
# Check API is running
curl http://localhost:8084/api/health

# Verify authentication works
curl -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}'

# Check Prisma AIRS is enabled
grep "Prisma AIRS" /tmp/api.log | head -5
```

### Frontend Health
- Navigate to https://sqlagent.dittmar.it
- Login with admin credentials
- Verify tabs are visible (Metrics, Assistant, Agent Health)
- Check Assistant tab shows ChatBot and Info Box
- Confirm no security section in Info Box

## Infrastructure

| Host | IP | Role | Status |
|------|-----|------|--------|
| arm1 | 10.0.2.176 | API Backend | ✅ Running |
| arm2 | 10.0.2.11 | Frontend | ✅ Deployed |
| vm1 | 10.0.1.189 | Monitored DB | ✅ Connected |
| vm2 | 10.0.1.214 | Load Generator | Connected |

## Maintenance Notes

### Monitoring Logs
```bash
# Backend logs
tail -f /tmp/api.log

# Security logs (Prisma AIRS)
grep "SECURITY:" /tmp/api.log

# Error logs
grep "ERROR\|exception" /tmp/api.log
```

### Common Issues

**502 Bad Gateway:**
- Backend not running: `python3 main.py run --config config.yaml`
- Check API health: `curl http://localhost:8084/api/health`

**Prisma AIRS blocks all requests:**
- Check API key and profile are set: `echo $PRISMA_AIRS_API_KEY $PRISMA_AIRS_PROFILE_NAME`
- Verify profile exists in Palo Alto console
- Restart backend after fixing environment

**UI not updating after deploy:**
- Clear browser cache (Ctrl+Shift+Del)
- Hard refresh (Ctrl+F5)
- Check /var/www/dashboard/ has latest dist files

## Documentation Files

- **README.md** — Features, architecture, security, quick start
- **CLAUDE.md** — Complete project context with Prisma AIRS details
- **frontend/README.md** — Component docs, deployment instructions
- **DEPLOYMENT_STATUS.md** — This file, current deployment state

## Next Steps

See CLAUDE.md "Next steps (not yet implemented)" section for planned enhancements.
