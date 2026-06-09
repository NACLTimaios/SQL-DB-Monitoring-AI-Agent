# LLM Provider Configuration Guide

This guide explains how to configure different LLM providers for the chatbot, including Prisma AI and other OpenAI-compatible endpoints.

## Overview

The application supports multiple LLM providers through a pluggable provider system:

| Provider | Status | Models | Configuration |
|----------|--------|--------|---|
| **Anthropic (Claude)** | ✅ Fully supported | 3 models | API key only |
| **Google (Gemini)** | ✅ Fully supported | 7+ models | API key only |
| **OpenAI (GPT)** | ✅ Fully supported | 2+ models | API key only |
| **Prisma AI** | ✅ Fully supported | Any | API key + endpoint URL |
| **Other OpenAI-compatible** | ✅ Compatible | Any | API key + endpoint URL |

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

## Google Gemini Models

### Available Models

Google offers multiple Gemini models optimized for different use cases:

#### Latest Models (Recommended)

**Gemini 2.0 Flash** - Newest, fastest
```bash
export LLM_PROVIDER=google
export LLM_MODEL=gemini-2.0-flash
export GOOGLE_API_KEY=your-api-key
```
- **Cost**: Low (~0.5¢ per 1M input tokens)
- **Speed**: Fastest inference
- **Best for**: Real-time queries, budget-conscious deployments
- **Context**: Latest capabilities

#### Gemini 1.5 Series (Stable)

**Gemini 1.5 Pro** - Best reasoning
```bash
export LLM_MODEL=gemini-1.5-pro
```
- **Cost**: Moderate (~$3 per 1M input tokens)
- **Speed**: Medium
- **Best for**: Complex analysis, multi-step reasoning
- **Context**: 2M tokens
- **Best for database monitoring**: Deep query analysis

**Gemini 1.5 Flash** - General purpose
```bash
export LLM_MODEL=gemini-1.5-flash
```
- **Cost**: Very cheap (~0.5¢ per 1M input tokens)
- **Speed**: Very fast
- **Best for**: Most database queries and analysis
- **Context**: 1M tokens
- **Best for database monitoring**: All tools work well

**Gemini 1.5 Flash-8B** - Lightweight
```bash
export LLM_MODEL=gemini-1.5-flash-8b
```
- **Cost**: Ultra cheap (~0.05¢ per 1M input tokens)
- **Speed**: Fastest
- **Best for**: Simple queries, low-resource environments
- **Context**: Optimized for efficiency
- **Note**: May struggle with very complex analysis

**Gemini 1.5 Flash-2B** - Ultra-lightweight
```bash
export LLM_MODEL=gemini-1.5-flash-2b
```
- **Cost**: Ultra cheap (~0.02¢ per 1M input tokens)
- **Speed**: Fastest
- **Best for**: Minimal resources, simple queries only
- **Note**: Limited reasoning capability

#### Multi-Modal Models (Images + Text)

**Gemini 1.5 Pro Vision**
```bash
export LLM_MODEL=gemini-1.5-pro-vision
```
- Can process images in addition to text
- All database monitoring features work
- Same cost as Gemini 1.5 Pro

**Gemini 1.5 Flash Vision**
```bash
export LLM_MODEL=gemini-1.5-flash-vision
```
- Can process images in addition to text
- All database monitoring features work
- Same cost as Gemini 1.5 Flash

### Model Selection Guide

| Use Case | Recommended Model | Reason |
|----------|-------------------|--------|
| **Best overall** | Gemini 2.0 Flash | Fast, cheap, latest |
| **Production deployment** | Gemini 1.5 Flash | Proven stable, very cheap |
| **Complex analysis** | Gemini 1.5 Pro | Better reasoning |
| **Budget constrained** | Gemini 1.5 Flash-8B | Cheapest that works |
| **Ultra-budget** | Gemini 1.5 Flash-2B | Bare minimum cost |
| **Images needed** | Gemini 1.5 Flash Vision | Can see screenshots/diagrams |

### Cost Comparison (per million input tokens)

```
Gemini 2.0 Flash:      $0.005  (cheapest + newest)
Gemini 1.5 Flash-2B:   $0.020  (ultra cheap, limited)
Gemini 1.5 Flash-8B:   $0.050  (very cheap, lightweight)
Gemini 1.5 Flash:      $0.500  (recommended)
Gemini 1.5 Pro:        $3.000  (advanced reasoning)

For 1000 database queries (avg 100 tokens each):
Gemini 2.0 Flash:    $0.50/month
Gemini 1.5 Flash-8B: $5.00/month
Gemini 1.5 Flash:    $50/month
Gemini 1.5 Pro:      $300/month
```

### Recommended Setup

For most database monitoring:
```bash
export LLM_PROVIDER=google
export LLM_MODEL=gemini-1.5-flash
export GOOGLE_API_KEY=your-google-api-key
python3 main.py run --config config.yaml
```

For budget deployments:
```bash
export LLM_MODEL=gemini-1.5-flash-8b  # Ultra cheap
```

For complex analysis:
```bash
export LLM_MODEL=gemini-1.5-pro  # Better reasoning
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
