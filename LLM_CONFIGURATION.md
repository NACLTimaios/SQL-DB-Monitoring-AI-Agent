# LLM Provider Configuration Guide

This guide explains how to configure different LLM providers for the chatbot, including Prisma AI and other OpenAI-compatible endpoints.

## Overview

The application supports multiple LLM providers through a pluggable provider system:

| Provider | Status | Configuration |
|----------|--------|---|
| **Anthropic (Claude)** | ✅ Fully supported | API key only |
| **Google (Gemini)** | ✅ Fully supported | API key only |
| **OpenAI (GPT)** | ✅ Fully supported | API key only |
| **Prisma AI** | ✅ Fully supported | API key + endpoint URL |
| **Other OpenAI-compatible** | ✅ Compatible | API key + endpoint URL |

## Storing API Keys and URLs Securely

### ✅ CORRECT - Use Environment Variables

**Location**: `.env` file (NOT in version control)

```bash
# .env (on server, 600 permissions)
PRISMA_API_KEY=your-actual-api-key-here
PRISMA_API_URL=https://api.prisma.ai
```

**Permissions**:
```bash
chmod 600 .env
```

### ❌ INCORRECT - DO NOT DO THIS

- ❌ Hardcode in Python files
- ❌ Commit to git/GitHub
- ❌ Store in world-readable files
- ❌ Log in application output

## Configuring Prisma AI

### Step 1: Set Environment Variables

Edit `.env` on your server:

```bash
# For Prisma AI
PRISMA_API_KEY=pk_live_xxxxxxxxxxxxx
PRISMA_API_URL=https://api.prisma.ai

# Or if using a self-hosted Prisma instance
PRISMA_API_URL=https://your-prisma-instance.com
```

**Important**: Never commit `.env` to git. It's excluded via `.gitignore`.

### Step 2: Update Configuration File

Set the LLM provider in your deployment configuration or via environment variable when running:

```bash
# Option A: Via environment when starting
export PRISMA_API_KEY="your-key"
export PRISMA_API_URL="https://api.prisma.ai"
python3 main.py run --config config.yaml

# Option B: Via config file
# Edit config.yaml:
llm_provider: prisma
llm_model: prisma-7b  # or your model name
```

### Step 3: Set Required Permissions

```bash
# Secure the .env file
chmod 600 .env

# Verify permissions
ls -la .env
# Should show: -rw------- 1 ubuntu ubuntu
```

## Environment Variables Reference

### For Prisma AI

```bash
# REQUIRED
PRISMA_API_KEY=your-api-key-here
PRISMA_API_URL=https://api.prisma.ai

# OPTIONAL (also used in config.yaml)
LLM_PROVIDER=prisma
LLM_MODEL=prisma-7b
```

### For Other Providers

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Google
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

## Configuration Location Map

### Where Secrets Are Stored

```
Development Machine:
├── .env                          ← API keys (600 permissions, gitignored)
├── .env.example                  ← Template (644 permissions, in git)
└── config.yaml                   ← Database credentials (600 permissions)

Production Server (arm1):
├── .env                          ← Your actual credentials
├── config.yaml                   ← Your actual database passwords
└── logs/audit.log               ← Audit trail of operations
```

### What Gets Committed to Git

```
GitHub Repository:
├── .env.example                  ← ONLY THIS - template with placeholders
├── orchestrator/llm_providers.py ← Code that uses API keys
├── README.md                     ← Configuration instructions
└── .gitignore                    ← Excludes .env from commits
```

### Security Checklist

- [x] `.env` is in `.gitignore` (never committed)
- [x] `.env.example` is in git (shows what variables are needed)
- [x] Environment variables used instead of hardcoding
- [x] `.env` file permissions set to 600 (user read/write only)
- [x] `config.yaml` permissions set to 600
- [x] No API keys logged in application output
- [x] Audit logging enabled for sensitive operations

## Deploying with Prisma AI

### On Your Server (arm1)

```bash
# 1. Clone repository
git clone https://github.com/your/repo.git
cd sql_agent

# 2. Create .env with your credentials
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
AGENT_DB_PASSWORD=your-password-here
MONITORED_DB_PASSWORD=your-password-here
CORS_ORIGINS=https://your-domain.com
ALLOWED_HOSTS=your-domain.com
PRISMA_API_KEY=your-prisma-key-here
PRISMA_API_URL=https://api.prisma.ai
EOF

# 3. Secure the file
chmod 600 .env

# 4. Install dependencies
pip install -r requirements.txt

# 5. Initialize database
python3 main.py init-db --config config.yaml

# 6. Start with Prisma AI
export LLM_PROVIDER=prisma
python3 main.py run --config config.yaml --log-level INFO
```

### Verification

Check that Prisma AI is being used:

```bash
# In application logs, you should see:
# "LLM Provider: prisma"
# "Model: <your-model-name>"

# Test the chatbot
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"SELECT * FROM customers LIMIT 1"}'
```

## Switching Between Providers

To switch from one provider to another:

```bash
# 1. Update .env with new provider's credentials
PRISMA_API_KEY=new-key
PRISMA_API_URL=new-url

# OR for Anthropic:
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 2. Restart application
pkill -f "python3 main.py run"
export LLM_PROVIDER=prisma  # or anthropic, google, openai
python3 main.py run --config config.yaml
```

## Troubleshooting

### Error: "PRISMA_API_KEY not configured"

**Solution**: Check that environment variable is set

```bash
# Verify variable is set
echo $PRISMA_API_KEY

# If empty, set it
export PRISMA_API_KEY="your-key-here"
```

### Error: "PRISMA_API_URL not configured"

**Solution**: Set the API endpoint URL

```bash
export PRISMA_API_URL="https://api.prisma.ai"
```

### Error: "Connection refused" or "API request failed"

**Solution**: Verify the endpoint is accessible

```bash
# Test connection to Prisma endpoint
curl -H "Authorization: Bearer $PRISMA_API_KEY" \
  "$PRISMA_API_URL/v1/models"

# Should return a list of available models
```

### Error: "401 Unauthorized"

**Solution**: Check that API key is correct

```bash
# Verify the key matches your Prisma account
echo $PRISMA_API_KEY

# Get correct key from https://prisma.ai/dashboard
# Update in .env and restart
```

## Best Practices

### 1. Use Strong, Unique Keys
```bash
# ❌ Don't use simple passwords
PRISMA_API_KEY=password123

# ✅ Use keys provided by Prisma
PRISMA_API_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx
```

### 2. Rotate Keys Regularly
```bash
# Every 90 days minimum
# 1. Generate new key in Prisma dashboard
# 2. Update .env with new key
# 3. Delete old key in Prisma dashboard
# 4. Restart application
```

### 3. Use Different Keys for Different Environments
```bash
# Development .env
PRISMA_API_KEY=pk_test_xxxxx

# Production .env (on server)
PRISMA_API_KEY=pk_live_xxxxx
```

### 4. Audit Access
```bash
# Check logs for API usage
tail -f logs/audit.log | grep -i prisma

# Monitor for unusual patterns
grep "error\|failed\|unauthorized" logs/agent.log
```

## API Compatibility

Prisma AI uses an OpenAI-compatible API, so any compatible endpoint works:

### Prisma AI Hosted
```
PRISMA_API_URL=https://api.prisma.ai
```

### Self-Hosted Prisma
```
PRISMA_API_URL=https://your-instance.local
```

### Other OpenAI-Compatible Endpoints
```
# Ollama
PRISMA_API_URL=http://localhost:11434

# vLLM
PRISMA_API_URL=http://localhost:8000

# Text Generation WebUI
PRISMA_API_URL=http://localhost:5000
```

## References

- [Prisma AI Documentation](https://docs.prisma.io)
- [OpenAI API Compatibility](https://platform.openai.com/docs/api-reference)
- [Environment Variables in Python](https://docs.python.org/3/library/os.html#os.environ)

---

**Last Updated**: 2026-06-08
**Status**: Prisma AI Support Added
