# Portkey AI Gateway Integration Guide

## Overview

Portkey AI is a unified AI API gateway that lets you:
- Route requests to multiple LLM providers (OpenAI, Google, Anthropic, etc.)
- Switch between models without code changes
- Use a single API key for all models
- Access advanced features like caching, retries, and analytics

This guide shows how to set up SQL Agent to use Portkey AI Gateway as your LLM provider.

## Prerequisites

- Portkey AI account (free tier available at [portkey.ai](https://portkey.ai))
- Portkey API key
- SQL Agent running on arm1
- Access to edit environment variables

## Setup Steps

### 1. Get Your Portkey API Key

1. Go to [portal.portkey.ai](https://portal.portkey.ai)
2. Sign up or log in
3. Navigate to **API Keys** section
4. Copy your API key (starts with `pk_...`)

### 2. Add Portkey API Key to Environment

Add the API key to your environment:

**Option A: Using .env file (Recommended)**
```bash
# Edit .env file in /home/ubuntu/sql_agent/
echo 'PORTKEY_API_KEY=your-api-key-here' >> /home/ubuntu/sql_agent/.env
```

**Option B: Export as environment variable**
```bash
export PORTKEY_API_KEY="your-api-key-here"
```

**Option C: Using systemd service (Production)**
Create `/etc/systemd/system/sql-agent.service` with:
```ini
[Service]
Environment="PORTKEY_API_KEY=your-api-key-here"
```

### 3. Restart the API

```bash
pkill -f "python3 main.py run"
sleep 2
bash /home/ubuntu/sql_agent/start_api.sh
```

Verify it started:
```bash
curl http://localhost:8084/api/health
```

### 4. Configure via Admin Settings

1. Go to https://sqlagent.dittmar.it
2. Click **Settings** (or **Admin Settings**)
3. Under **Chatbot Settings** → **LLM Provider**, select **🔀 Portkey AI Gateway**
4. Select a route from the **Route** dropdown

Available routes:
- `@geminiapi/gemini-2.5-flash` — Google Gemini (fast, low cost)
- `@geminiapi/gemini-2.5-pro` — Google Gemini (more capable)
- `@openaiapi/gpt-4o` — OpenAI GPT-4o
- `@openaiapi/gpt-4-turbo` — OpenAI GPT-4 Turbo
- `@anthropicapi/claude-3-5-sonnet` — Anthropic Claude
- `@anthropicapi/claude-3-haiku` — Anthropic Claude (lightweight)

5. Click **Save Configuration**

### 5. Start Using

Open the **Assistant** tab and start asking questions. The chatbot will now route requests through Portkey!

## Portkey Route Format

Portkey uses a special format for specifying model routes:

```
@<provider>api/<model-name>
```

Examples:
- `@geminiapi/gemini-2.5-flash` → Routes to Google Gemini 2.5 Flash via Portkey
- `@openaiapi/gpt-4o` → Routes to OpenAI GPT-4o via Portkey
- `@anthropicapi/claude-3-5-sonnet` → Routes to Anthropic Claude via Portkey

## Verify Setup

### Check via API

```bash
# Get current config
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8084/api/chatbot/config | jq .

# Should show:
# {
#   "llm_provider": "portkey",
#   "llm_model": "@geminiapi/gemini-2.5-flash",
#   ...
# }
```

### Check via Admin Settings

1. Go to Admin Settings
2. Look at the **Gateway** section
3. Should show:
   - **Provider:** Portkey AI Gateway
   - **Route:** Your selected route

## Assistant Tab Display

When using Portkey, the Assistant tab info box shows:

```
🔀 Gateway

Provider: Portkey AI Gateway
Route: @geminiapi/gemini-2.5-flash

✓ Requests routed through Portkey AI Gateway
✓ Configured via PORTKEY_API_KEY environment variable
```

## Advanced Configuration

### Custom Routes

To use a custom Portkey route (beyond the defaults), edit `/home/ubuntu/sql_agent/api/server.py` at line 995 and add your route:

```python
"portkey": [
    "@geminiapi/gemini-2.5-flash",
    "@openaiapi/gpt-4o",
    "@your-custom-route/model-name",  # Add custom routes here
],
```

Then restart the API.

### Switching Models Dynamically

You can switch models at runtime via Admin Settings without restarting:

1. Go to Admin Settings
2. Select a different route from dropdown
3. Click Save
4. The next chat message will use the new model

### Using Portkey Dashboard

Portkey provides a dashboard for analytics:

1. Log in to [portal.portkey.ai](https://portal.portkey.ai)
2. View usage analytics
3. Check request logs
4. Monitor costs across all models

## Troubleshooting

### "PORTKEY_API_KEY not configured"

**Problem:** Error message says API key not configured

**Solution:**
```bash
# Check if environment variable is set
echo $PORTKEY_API_KEY

# If empty, add to .env
echo 'PORTKEY_API_KEY=pk_...' >> /home/ubuntu/sql_agent/.env

# Restart API
bash /home/ubuntu/sql_agent/start_api.sh
```

### "Route not found" or Model errors

**Problem:** Invalid route specified

**Solution:**
- Use routes in exact format: `@providerapi/model-name`
- Check capitalization (e.g., `geminiapi` not `geminapi`)
- Verify route is available in Portkey console

Common mistakes:
- ❌ `gemini-2.5-flash` (missing `@geminiapi/`)
- ❌ `@geminapi/gemini-2.5-flash` (typo: should be `geminiapi`)
- ✅ `@geminiapi/gemini-2.5-flash`

### Requests timing out

**Problem:** Portkey API requests are slow or timing out

**Solution:**
1. Check Portkey service status: https://status.portkey.ai
2. Verify API key is valid: Try making a test request from Portkey console
3. Check internet connectivity on arm1
4. Try a different route (some models may be slower)

### Can't see Portkey option in Admin Settings

**Problem:** "🔀 Portkey AI Gateway" option not visible

**Solution:**
1. Clear browser cache: `Ctrl+Shift+Delete`
2. Hard refresh: `Ctrl+F5`
3. Verify frontend was redeployed: Check `/var/www/dashboard/assets/` for latest files

## Cost Optimization

Portkey lets you optimize costs:

### Use Cheaper Models
- **Best value:** `@geminiapi/gemini-2.5-flash` (fast + cheap)
- **Fast + accurate:** `@anthropicapi/claude-3-haiku`
- **Most capable:** `@openaiapi/gpt-4o` (costs more)

### Portkey Features
- **Caching** — Avoid re-processing identical requests
- **Retries** — Automatic fallback on failures
- **Load balancing** — Distribute across multiple providers

Configure these in your Portkey dashboard.

## Security

### API Key Protection

- ✅ API key stored in `.env` (not in code)
- ✅ Environment variable `PORTKEY_API_KEY` (not exposed to frontend)
- ✅ Never logged in plain text
- ✅ Requests include authentication header

### Data Privacy

- Portkey acts as a routing layer
- Your database queries are still sent through Portkey's API
- Check Portkey's privacy policy: https://portkey.ai/privacy

## Examples

### Example 1: Using Gemini

```
1. Admin Settings → Portkey AI Gateway
2. Select: @geminiapi/gemini-2.5-flash
3. Save
4. Open Assistant tab
5. Ask: "Show me top 5 customers"
6. ✓ Request routed through Portkey → Google Gemini
```

### Example 2: Switching to GPT-4o

```
1. Currently using Gemini
2. Admin Settings → Change to: @openaiapi/gpt-4o
3. Save
4. Next message: "What's the database schema?"
5. ✓ Request now routes through Portkey → OpenAI GPT-4o
```

### Example 3: Custom Model Weights

In Portkey console, you can set model weights:
- 70% Gemini Flash (fast + cheap)
- 30% GPT-4o (accurate for complex queries)

Portkey automatically routes based on weights!

## Documentation Links

- **Portkey Docs:** https://docs.portkey.ai
- **Portkey Console:** https://portal.portkey.ai
- **Portkey Status:** https://status.portkey.ai
- **Python SDK:** https://github.com/Portkey-AI/portkey-python-sdk

## Getting Help

### If Portkey stops working:

1. **Check logs:**
   ```bash
   tail -50 /tmp/api.log | grep -i portkey
   ```

2. **Test API key:**
   ```bash
   curl -X POST https://api.portkey.ai/v1/chat/completions \
     -H "Authorization: Bearer $PORTKEY_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "@geminiapi/gemini-2.5-flash",
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

3. **Check Portkey status:** https://status.portkey.ai

4. **Restart API:**
   ```bash
   bash /home/ubuntu/sql_agent/start_api.sh
   ```

---

**Last Updated:** June 18, 2026
**Portkey Integration Version:** 1.0
