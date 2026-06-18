# Portkey Integration - Quick Start (5 minutes)

## What's Ready

✅ **Backend:** Portkey provider fully implemented  
✅ **Frontend:** Admin page shows Portkey option  
✅ **Assistant tab:** Displays gateway info  
✅ **Package:** `portkey-ai` SDK installed  

## What You Need

You only need to provide your **Portkey API key**. That's it!

## 3-Step Setup

### 1️⃣ Get Your API Key (1 min)

1. Go to https://portal.portkey.ai
2. Sign up (free tier available)
3. Copy your API key (looks like `pk_...`)

### 2️⃣ Add API Key to Environment (1 min)

```bash
# Add to .env file
echo 'PORTKEY_API_KEY=your-key-here' >> /home/ubuntu/sql_agent/.env

# Restart API
pkill -f "python3 main.py run"
sleep 2
bash /home/ubuntu/sql_agent/start_api.sh
```

Verify it restarted:
```bash
curl http://localhost:8084/api/health
```

### 3️⃣ Configure in Admin Settings (1 min)

1. Go to https://sqlagent.dittmar.it
2. Click **Settings** → **Chatbot Settings**
3. Under **LLM Provider**, select: **🔀 Portkey AI Gateway**
4. Under **Route**, select a model:
   - Recommended: `@geminiapi/gemini-2.5-flash` (fast + cheap)
   - Or: `@openaiapi/gpt-4o`, `@anthropicapi/claude-3-5-sonnet`
5. Click **Save Configuration**

✅ **Done!** You're now using Portkey!

## That's All!

Open the **Assistant** tab and start asking questions. Your requests will now be routed through Portkey.

The **Assistant Info** box will show:

```
🔀 Gateway

Provider: Portkey AI Gateway
Route: @geminiapi/gemini-2.5-flash

✓ Requests routed through Portkey AI Gateway
✓ Configured via PORTKEY_API_KEY environment variable
```

## What Portkey Does

Once configured, Portkey:
- Routes all your requests to the provider you selected
- Provides analytics and cost tracking
- Supports caching, retries, load balancing
- Lets you switch models anytime without code changes

## Common Routes

| Route | Provider | Speed | Cost |
|-------|----------|-------|------|
| `@geminiapi/gemini-2.5-flash` | Google | ⚡ Fast | 💰 Cheap |
| `@geminiapi/gemini-2.5-pro` | Google | ⚡⚡ Faster | 💰💰 Moderate |
| `@openaiapi/gpt-4o` | OpenAI | ⚡⚡⚡ Fastest | 💰💰💰 Expensive |
| `@anthropicapi/claude-3-5-sonnet` | Anthropic | ⚡⚡ Medium | 💰💰 Moderate |
| `@anthropicapi/claude-3-haiku` | Anthropic | ⚡ Fast | 💰 Cheap |

## Troubleshooting

**"PORTKEY_API_KEY not configured"**
```bash
# Check if set
echo $PORTKEY_API_KEY

# If empty, add and restart
echo 'PORTKEY_API_KEY=pk_...' >> .env
bash /home/ubuntu/sql_agent/start_api.sh
```

**"Route not found" error**
- Make sure route format is exact: `@providerapi/model-name`
- Check capitalization
- Valid examples: `@geminiapi/gemini-2.5-flash`, `@openaiapi/gpt-4o`

## For More Details

See **[PORTKEY_SETUP.md](PORTKEY_SETUP.md)** for:
- Full setup with examples
- Advanced configuration
- Cost optimization
- Security details

---

**That's it! You're ready to use Portkey.** 🚀
