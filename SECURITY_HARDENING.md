# Security Hardening Guide for Production Deployment

## Status: CRITICAL FIXES APPLIED ✅

This document tracks the security fixes applied to make the application production-ready.

## Applied Critical Fixes

### 1. ✅ JWT Secret Key Enforcement
- **Issue**: Weak default JWT secret key allowing token forgery
- **Fix**: Require `SECRET_KEY` environment variable at startup
- **Files**: `api/auth.py`
- **Action**: Set `SECRET_KEY` to a secure random value before deployment
- **Test**: Application will fail to start if SECRET_KEY is not set

### 2. ✅ Secure Admin User Initialization
- **Issue**: Hardcoded admin password "changeme" in source code
- **Fix**: Generate secure random password on first user creation, output to stderr only
- **Files**: `api/auth.py`
- **Action**: Capture the generated password from startup logs and save securely
- **Test**: Check stderr output during first application startup

### 3. ✅ SQL Injection Prevention
- **Issue**: User input directly interpolated into SQL queries
- **Fix**: Implemented parameterized queries using psycopg2 prepared statements
- **Files**: `orchestrator/chatbot_service.py`, `config/loader.py`
- **Action**: All user inputs are now safely parameterized
- **Test**: Try various SQL injection payloads - they will be treated as literal strings

### 4. ✅ Environment-Based Credentials
- **Issue**: Hardcoded database passwords in config.yaml
- **Fix**: Config loader now supports `${VAR_NAME}` environment variable interpolation
- **Files**: `config/loader.py`, `config.yaml`, `.env.example`
- **Action**: Set environment variables before starting application:
  ```bash
  export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  export AGENT_DB_PASSWORD="secure-password"
  export MONITORED_DB_PASSWORD="secure-password"
  ```
- **Test**: Application loads without plaintext credentials in memory

## Applied High-Severity Fixes

### 5. ✅ Restrictive CORS Configuration
- **Issue**: `allow_origins=["*"]` accepting all cross-origin requests
- **Fix**: Restricted to specific origins via environment variable
- **Files**: `api/server.py`
- **Configuration**:
  ```bash
  export CORS_ORIGINS="https://sqlagent.example.com"
  export ALLOWED_HOSTS="sqlagent.example.com"
  ```

### 6. ✅ Security Headers
- **Issue**: Missing security headers (CSP, HSTS, X-Frame-Options, etc.)
- **Fix**: Added SecurityHeadersMiddleware with comprehensive security headers
- **Headers Added**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000`
  - `Content-Security-Policy: default-src 'self'`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### 7. ✅ Reduced Token Expiry
- **Issue**: 24-hour token expiry is too long
- **Fix**: Reduced to 30 minutes (configurable via environment variable)
- **Files**: `api/auth.py`
- **Configuration**: `ACCESS_TOKEN_EXPIRE_MINUTES=30`

## Remaining High-Priority Items

These require additional implementation but don't block deployment:

### Input Validation on Endpoints
- Add Pydantic field validators for username/password strength
- Minimum password length: 12 characters
- Require uppercase, lowercase, numbers, special characters

### Rate Limiting
- Implement slowapi rate limiter
- Login: 5 attempts per minute per IP
- User creation: 10 attempts per minute per IP
- API endpoints: 100 requests per minute per token

### Audit Logging
- Log all sensitive operations (login, user creation, config changes)
- Include timestamp, user, action, IP address, result
- Store in separate audit log file with restricted permissions (600)

### Configuration Security
- Set config.yaml permissions to 600 (user read/write only)
- Set .env file permissions to 600
- Never commit .env files to version control

### Dependency Updates
- Update all npm packages to latest versions
- Update Python packages to latest versions
- Implement regular security scanning with `npm audit`, `pip audit`

## Frontend Security Checklist

### ✅ Implemented
- Token stored in localStorage (with HTTPS in production)
- Authorization headers on all API requests
- Proper error handling without exposing sensitive information

### 📋 Recommended
- Implement refresh token mechanism
- Add CSRF token to form submissions
- Validate all user inputs on frontend
- Use Content Security Policy headers
- Keep React and dependencies updated
- Implement rate limiting on frontend (prevent duplicate submissions)

## Database Security

### Current Status
- Monitoring user has read-only permissions on monitored database ✅
- PostgreSQL requires password authentication ✅
- Credentials stored in environment variables ✅

### Recommendations
- Run PostgreSQL on private network (not exposed to internet)
- Enable PostgreSQL audit logging
- Implement connection pooling with SSL/TLS
- Regular database backups with encryption
- Monitor and log database connections

## Deployment Checklist

Before deploying to production:

### Backend (arm1)
- [ ] Set `SECRET_KEY` environment variable
- [ ] Set `AGENT_DB_PASSWORD` environment variable
- [ ] Set `MONITORED_DB_PASSWORD` environment variable
- [ ] Set `CORS_ORIGINS` to your frontend URL
- [ ] Set `ALLOWED_HOSTS` to your domain names
- [ ] Update LLM API keys (ANTHROPIC_API_KEY, etc.)
- [ ] Verify SSL/TLS certificates
- [ ] Test application startup - verify admin password appears in stderr
- [ ] Test JWT token creation and expiry
- [ ] Test CORS on allowed origins
- [ ] Verify security headers with curl: `curl -i https://your-domain/api/health`

### Frontend (arm2)
- [ ] Build with production settings
- [ ] Verify HTTPS is enabled
- [ ] Test API calls to backend (should respect CORS)
- [ ] Verify CSP headers don't block your assets
- [ ] Test error handling without exposing sensitive info

### Infrastructure
- [ ] Configure firewall to allow only necessary ports (80, 443, 22)
- [ ] Restrict SSH access to specific IPs
- [ ] Enable HTTPS with valid SSL/TLS certificate
- [ ] Configure automated certificate renewal
- [ ] Enable access logging for audit trail
- [ ] Set up log rotation

### Operations
- [ ] Document all environment variables
- [ ] Store credentials in secure vault (not in code/config files)
- [ ] Implement secrets rotation policy
- [ ] Set up monitoring and alerting
- [ ] Plan incident response procedures
- [ ] Schedule regular security audits

## Testing Security Fixes

### Test SQL Injection Prevention
```bash
# This should return "No customers found" not execute malicious SQL
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "show credit card for CompanyBot'\'') DROP TABLE customers; --"}'
```

### Test JWT Secret Key Requirement
```bash
# Try starting app without SECRET_KEY - should fail
unset SECRET_KEY
python3 main.py run --config config.yaml
# Expected: RuntimeError about missing SECRET_KEY
```

### Test CORS Restrictions
```bash
# From allowed origin - should succeed
curl -X GET http://localhost:8084/api/health \
  -H "Origin: http://localhost:3000"

# From disallowed origin - should fail
curl -X GET http://localhost:8084/api/health \
  -H "Origin: http://evil.com"
```

### Test Security Headers
```bash
curl -i http://localhost:8084/api/health | grep -E "X-|Content-Security|Strict-Transport"
# Should see all security headers in response
```

## Files Modified

- `api/auth.py` - JWT secret key enforcement, secure admin user creation
- `api/server.py` - Restrictive CORS, security headers, TrustedHost middleware
- `orchestrator/chatbot_service.py` - Parameterized SQL queries
- `config/loader.py` - Environment variable interpolation
- `config.yaml` - Use environment variables for credentials
- `.env.example` - Template for environment variables (NEW)
- `SECURITY_HARDENING.md` - This document (NEW)

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- OWASP Security Headers: https://owasp.org/www-project-secure-headers/
- PostgreSQL Security: https://www.postgresql.org/docs/current/sql-syntax.html
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/

## Support

For security concerns or vulnerability reports, please:
1. Do NOT publicly disclose the vulnerability
2. Document the issue with proof-of-concept
3. Follow responsible disclosure practices
4. Contact the security team with details

---

**Last Updated**: 2026-06-08
**Status**: Production Security Hardening Complete
