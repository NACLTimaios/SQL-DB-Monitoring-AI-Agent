# Security & Production Readiness

This document is the security overview for the SQL Agent. It was moved out of the
main README to keep that file focused. For deeper detail, see the linked documents
at the bottom.

## Current Status
- ✅ **PRODUCTION-READY** with proper environment configuration
- ✅ All critical security vulnerabilities have been fixed
- ✅ OWASP Top 10 mitigations implemented
- ✅ Comprehensive security audit completed (2026-06-08)

## Security Hardening Applied (June 2026)

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

**AI Security: Prisma AIRS Integration (June 2026)**
- ✅ **Three-Stage Scanning** - User prompts, tool outputs, and LLM responses all scanned for threats
- ✅ **Prompt Scanning** - Detects injection attacks, prompt theft, jailbreaks BEFORE LLM receives input
- ✅ **Tool Output Scanning** - Detects sensitive data in tool results BEFORE LLM processes them
- ✅ **Response Scanning** - Detects data leakage, malicious output AFTER LLM generates response
- ✅ **Fail-Closed Design** - If scanner unavailable, requests are BLOCKED to prevent silent data leakage (security-first)
- ✅ **Detection-Driven Blocking** - Content is blocked on what Prisma *detects* (malicious category or any threat detection), not only when the gateway's action policy says "block". This is defense-in-depth: a log-only profile still results in a block.
- ✅ **Profile-Based Detection** - Uses Palo Alto AI Security profile for advanced threat modeling
- ✅ **Profile Name Priority** - Prefers PRISMA_AIRS_PROFILE_NAME over ID for reliability
- ✅ **Audit Logging** - All blocks and scans logged to security audit trail
- ✅ **Guaranteed Protection** - If Prisma AIRS blocks content, data never reaches the LLM

**OWASP Top 10 Coverage:**
- ✅ A01:2021 – Broken Access Control (JWT + RBAC + rate limiting)
- ✅ A02:2021 – Cryptographic Failures (env vars, parameterized queries, Argon2)
- ✅ A03:2021 – Injection (parameterized SQL + Prisma AIRS prompt scanning)
- ✅ A04:2021 – Insecure Design (input validation, password strength)
- ✅ A05:2021 – CORS attacks (CORS restrictions)
- ✅ A06:2021 – Security Misconfiguration (security headers, config validation, file permissions)
- ✅ A07:2021 – Authentication Failures (secure password generation, token expiry, rate limiting)

## Production Deployment Checklist

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

## Planned for Future Releases

- Token refresh mechanism (sliding window)
- Secrets management system integration (HashiCorp Vault)
- Automated security scanning in CI/CD pipeline
- SSH key rotation policy
- Database backup encryption

## Detailed Security Documentation

- **[SECURITY_HARDENING.md](SECURITY_HARDENING.md)** - Complete security hardening guide with deployment checklist
- **[SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)** - Vulnerability assessment and remediation
- **[PRISMA_API_SECURITY.md](PRISMA_API_SECURITY.md)** - API key isolation guarantee
- **[PRISMA_AIRS_GUIDE.md](PRISMA_AIRS_GUIDE.md)** - Prisma AIRS three-stage scanning guide
- **[.env.example](.env.example)** - Template for required environment variables
