# LLM Provider Setup Guide

This guide explains how to configure the chatbot to use different LLM providers: Anthropic Claude, Google Gemini, or OpenAI GPT.

## Architecture Overview

The chatbot uses a **provider abstraction layer** that allows seamless switching between different LLM providers:

```
ChatbotService
    ↓
get_provider() factory
    ├─ AnthropicProvider
    ├─ GoogleProvider
    └─ OpenAIProvider
        ↓
    Provider's chat() method
        ↓
    LLM API (Anthropic/Google/OpenAI)
        ↓
    Tool execution (shared)
        ↓
    Database
```

**Key Features:**
- No API endpoint changes needed when switching providers
- No frontend changes needed
- All guardrails and tools work the same across providers
- Provider-specific tool/function calling handled internally
- Easy to add new providers

## Supported Providers

### 1. Anthropic Claude (Default)

**Pros:**
- Industry-leading performance on code and analysis
- Excellent at tool use
- Best at following instructions precisely
- Strong context window (200K tokens)

**Cons:**
- Higher cost per token
- Rate limits apply

**Setup:**

```bash
# Install dependency
pip install anthropic

# Get API key
# Visit: https://console.anthropic.com/account/keys
# Create key and copy (format: sk-ant-...)

# Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Or add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
source .env
```

**Supported Models:**
- `claude-3-opus-20250219` - Largest, most capable
- `claude-3-5-sonnet-20241022` - Default, best balance
- `claude-3-haiku-20240307` - Smallest, fastest
- `claude-4-1-preview` - Upcoming, if available

**Configure:**

Via AdminPage:
- Set Provider: "Anthropic"
- Set Model: "claude-3-5-sonnet-20241022"
- Click Save

Via API:
```bash
curl -X POST http://localhost:8084/api/chatbot/config \
  -H "Authorization: Bearer <token>" \
  -d '{
    "llm_provider": "anthropic",
    "llm_model": "claude-3-5-sonnet-20241022"
  }'
```

### 2. Google Gemini

**Pros:**
- Fast responses
- Good at complex reasoning
- Competitive pricing
- Excellent at multimodal tasks

**Cons:**
- Tool use still developing
- Smaller context window (100K tokens)

**Setup:**

```bash
# Install dependency
pip install google-generativeai

# Get API key
# Visit: https://makersuite.google.com/app/apikey
# Click "Create API Key"
# Copy the key (format: AIzaSy...)

# Set environment variable
export GOOGLE_API_KEY="AIzaSy..."

# Or add to .env file
echo "GOOGLE_API_KEY=AIzaSy..." >> .env
source .env
```

**Supported Models:**
- `gemini-2.0-flash` - Latest, fastest
- `gemini-1.5-pro` - Most capable
- `gemini-1.5-flash` - Balanced
- `gemini-pro` - Previous generation

**Configure:**

Via AdminPage:
- Set Provider: "google" (note: lowercase in config)
- Set Model: "gemini-1.5-pro"
- Click Save

Via API:
```bash
curl -X POST http://localhost:8084/api/chatbot/config \
  -H "Authorization: Bearer <token>" \
  -d '{
    "llm_provider": "google",
    "llm_model": "gemini-1.5-pro"
  }'
```

### 3. OpenAI GPT

**Pros:**
- Well-established, reliable
- Excellent performance on most tasks
- Good tool/function calling support
- Largest community

**Cons:**
- Higher cost
- Shorter context window (128K tokens for GPT-4)
- More expensive for long conversations

**Setup:**

```bash
# Install dependency
pip install openai

# Get API key
# Visit: https://platform.openai.com/api-keys
# Click "Create new secret key"
# Copy the key (format: sk-...)

# Set environment variable
export OPENAI_API_KEY="sk-..."

# Or add to .env file
echo "OPENAI_API_KEY=sk-..." >> .env
source .env
```

**Supported Models:**
- `gpt-4-turbo` - Most capable (recommended)
- `gpt-4` - Previous generation
- `gpt-4o` - Optimized variant (if available)
- `gpt-3.5-turbo` - Budget option

**Configure:**

Via AdminPage:
- Set Provider: "openai" (note: lowercase in config)
- Set Model: "gpt-4-turbo"
- Click Save

Via API:
```bash
curl -X POST http://localhost:8084/api/chatbot/config \
  -H "Authorization: Bearer <token>" \
  -d '{
    "llm_provider": "openai",
    "llm_model": "gpt-4-turbo"
  }'
```

## Switching Between Providers

### Step 1: Install Required SDK

```bash
# For the provider you want to use
pip install anthropic          # For Anthropic
pip install google-generativeai # For Google
pip install openai             # For OpenAI
```

### Step 2: Get API Key

See provider-specific setup section above.

### Step 3: Set Environment Variable

```bash
# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# For Google
export GOOGLE_API_KEY="AIzaSy..."

# For OpenAI
export OPENAI_API_KEY="sk-..."
```

### Step 4: Update Configuration

**Option A: AdminPage (Easiest)**
1. Login to dashboard
2. Click "Admin Settings" or navigate to `/admin`
3. Change "LLM Provider" dropdown
4. Change "Model Name" field
5. Click "Save Configuration"
6. Verify success message

**Option B: API Call**
```bash
TOKEN=$(curl -s -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"agentadmin","password":"Poseidon#x10"}' | jq -r .access_token)

curl -X POST http://localhost:8084/api/chatbot/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_provider": "google",
    "llm_model": "gemini-1.5-pro"
  }'
```

**Option C: Direct Database**
```sql
UPDATE chatbot_config SET 
  llm_provider = 'google',
  llm_model = 'gemini-1.5-pro'
WHERE id = 1;
```

### Step 5: Test Configuration

```bash
# Run test script
python3 scripts/test_chatbot.py

# Or test manually
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"How many customers are in the database?"}'
```

## Comparing Providers

| Aspect | Anthropic | Google | OpenAI |
|--------|-----------|--------|--------|
| **Speed** | Medium | Fast | Medium |
| **Cost** | Higher | Medium | Higher |
| **Tool Use** | Excellent | Good | Good |
| **Context Window** | 200K | 100K | 128K |
| **Setup Complexity** | Easy | Easy | Easy |
| **Maturity** | Mature | Growing | Very Mature |
| **Database Queries** | Excellent | Good | Good |

**Recommendation for Database Monitoring:**
- **Best overall:** Anthropic Claude (tool use + accuracy)
- **Best speed/cost:** Google Gemini
- **Enterprise:** OpenAI GPT-4 (established)

## Cost Estimation

Assuming ~100 chat messages per month, 500 tokens per message:

**Anthropic Claude 3.5 Sonnet:**
- Input: $0.003 per 1K tokens × 50K = $0.15
- Output: $0.015 per 1K tokens × 50K = $0.75
- **Total: ~$0.90/month**

**Google Gemini 1.5 Pro:**
- Input: $0.0025 per 1K tokens × 50K = $0.125
- Output: $0.01 per 1K tokens × 50K = $0.50
- **Total: ~$0.625/month**

**OpenAI GPT-4 Turbo:**
- Input: $0.01 per 1K tokens × 50K = $0.50
- Output: $0.03 per 1K tokens × 50K = $1.50
- **Total: ~$2.00/month**

*Note: Actual costs depend on usage patterns and API pricing*

## Troubleshooting

### "API key not configured"

**Cause:** Environment variable not set or API server restarted without the variable.

**Solution:**
```bash
# Verify variable is set
echo $ANTHROPIC_API_KEY  # or $GOOGLE_API_KEY or $OPENAI_API_KEY

# If empty, set it
export ANTHROPIC_API_KEY="sk-ant-..."

# Restart API
pkill -f "python3 main.py run"
python3 main.py run --config config.yaml
```

### "Unknown LLM provider"

**Cause:** Provider name misspelled or doesn't exist.

**Solution:**
- Valid providers: `anthropic`, `google`, `openai` (lowercase)
- Check spelling: `echo $llm_provider`
- View config: `curl http://localhost:8084/api/chatbot/config`

### Provider works but responses are slow

**Cause:** API rate limiting or network latency.

**Solution:**
1. Check provider status page:
   - Anthropic: https://status.anthropic.com
   - Google: https://status.cloud.google.com
   - OpenAI: https://status.openai.com

2. Increase nginx timeout:
   ```nginx
   location /api/chatbot/chat {
       proxy_read_timeout 180s;  # 3 minutes
       proxy_connect_timeout 30s;
   }
   ```

3. Consider switching to faster provider (Gemini usually fastest)

### Tool calls not working

**Cause:** Provider's tool/function calling format not properly implemented.

**Solution:**
- All 5 tools should work with all providers
- If one tool consistently fails, check server logs:
  ```bash
  tail -100 /tmp/api.log
  ```
- Report issue with specific provider + tool name

### Chat responses are inconsistent

**Cause:** Different providers behave differently on database queries.

**Solution:**
- Anthropic: Best for precise database queries
- Google: Faster but sometimes less accurate
- OpenAI: Good balance

Try adjusting system_prompt in AdminPage to guide the provider better.

## Adding a New Provider

To add support for another LLM provider:

1. **Create provider class** in `orchestrator/llm_providers.py`:
   ```python
   class CustomProvider(LLMProvider):
       def chat(self, user_message: str, available_tools: dict) -> ProviderResponse:
           # Implement provider API calls
           pass
   ```

2. **Add to factory** in `get_provider()`:
   ```python
   providers = {
       "anthropic": AnthropicProvider,
       "google": GoogleProvider,
       "openai": OpenAIProvider,
       "custom": CustomProvider,  # Add here
   }
   ```

3. **Install SDK** in `requirements.txt`:
   ```
   custom-sdk==1.0.0
   ```

4. **Update documentation** with setup instructions

## Performance Notes

### Latency by Provider
- **Google Gemini:** ~0.5-1s average
- **Anthropic Claude:** ~1-2s average
- **OpenAI GPT-4:** ~1-3s average

### Throughput (messages/second)
- All providers: 1-10 depending on model and load

### Cost-Performance Ratio
- **Best value:** Google Gemini
- **Best performance:** Anthropic Claude
- **Most reliable:** OpenAI GPT-4

## Environment Setup Examples

### .env File
```bash
# Anthropic setup
ANTHROPIC_API_KEY=sk-ant-...

# Or Google
GOOGLE_API_KEY=AIzaSy...

# Or OpenAI  
OPENAI_API_KEY=sk-...

# Other settings
SECRET_KEY=your-secret-key
```

### Docker Setup
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Set API key at runtime
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
# or GOOGLE_API_KEY or OPENAI_API_KEY

COPY . .
CMD ["python3", "main.py", "run", "--config", "config.yaml"]
```

### systemd Service
```ini
[Service]
Environment="ANTHROPIC_API_KEY=sk-ant-..."
ExecStart=/home/ubuntu/sql_agent/venv/bin/python3 main.py run --config config.yaml
```

## FAQ

**Q: Can I use multiple API keys for different providers?**
A: Yes, set all environment variables. The active provider is determined by `llm_provider` in config.

**Q: What happens if API key is invalid?**
A: Chat endpoint returns error in response. Check configuration in AdminPage.

**Q: Can I change providers mid-conversation?**
A: Yes, but new messages will use the new provider. Chat history is preserved.

**Q: Which provider is best for database queries?**
A: Anthropic Claude is most reliable for SQL queries due to superior tool use.

**Q: Do tools work the same across all providers?**
A: Yes, all 5 tools (query_database, get_metrics, etc.) work identically.

**Q: How do I know which provider is currently active?**
A: Check AdminPage or query: `curl http://localhost:8084/api/chatbot/config`

**Q: Can I use a custom/local LLM?**
A: Create a custom provider class following the LLMProvider pattern.
