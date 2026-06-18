# SQL Agent Dashboard - Frontend Components

This directory contains React components for the SQL Agent dashboard, including the chatbot interface, admin configuration panel, and information panels.

## Components

### ChatBot.tsx
A real-time chat interface for querying the database through multiple LLM providers (Anthropic Claude, Google Gemini, OpenAI GPT).

**Features:**
- Send natural language questions about the database
- Displays tool usage for each query
- Auto-scrolling message history
- Error handling and loading states
- Persistent chat history via API

**Integration:**
```tsx
import ChatBot from './components/ChatBot';

// In your dashboard layout:
<ChatBot />
```

### ChatbotInfoBox.tsx
Information panel for the Assistant tab showing chatbot configuration and available tools.

**Features:**
- Displays current LLM model and provider
- Lists available database tools with descriptions
- Shows guardrails status (write protection, DDL, timeouts, row limits)
- Links to Admin Settings for configuration
- Clean, dark-themed UI consistent with dashboard

**Integration:**
```tsx
import ChatbotInfoBox from './components/ChatbotInfoBox';

// Typically placed next to ChatBot in a grid:
<div className="grid grid-cols-3 gap-4">
  <div className="col-span-2"><ChatBot /></div>
  <div><ChatbotInfoBox /></div>
</div>
```

**Security Note:** Security scanning (Prisma AIRS) is configured server-side and operates transparently. The info box does not display security status — all prompts, tool outputs, and responses are scanned automatically if configured.

### AdminPage.tsx
Configuration dashboard for the chatbot system.

**Features:**
- LLM provider and model selection
- System prompt customization
- Tool enable/disable toggles
- Safety guardrails configuration (timeouts, row limits, write protection)
- Real-time validation and save feedback

**Integration:**
```tsx
import AdminPage from './pages/AdminPage';

// In your routing:
<Route path="/admin" element={<AdminPage />} />
```

## Setup Instructions

### Prerequisites
- Node.js 16+ and npm
- Existing React/TypeScript dashboard project
- API backend running on port 8084

### Installation

1. **Copy components to your project:**
   ```bash
   cp src/components/ChatBot.tsx /path/to/dashboard/src/components/
   cp src/pages/AdminPage.tsx /path/to/dashboard/src/pages/
   ```

2. **Install dependencies (if not already installed):**
   ```bash
   npm install axios
   ```

3. **Add routes to your App.tsx:**
   ```tsx
   import ChatBot from './components/ChatBot';
   import AdminPage from './pages/AdminPage';
   
   // In your router:
   <Route path="/admin" element={<AdminPage />} />
   ```

4. **Add ChatBot to your dashboard layout:**
   ```tsx
   <div className="grid grid-cols-2 gap-4">
     {/* Existing panels */}
     <ChatBot />
   </div>
   ```

### API Endpoints Required

The components expect these API endpoints to be available on `/api`:

- `POST /api/chatbot/chat` - Send a message
- `GET /api/chatbot/config` - Retrieve current configuration
- `POST /api/chatbot/config` - Update configuration
- `GET /api/chatbot/history` - Get chat message history
- `GET /api/chatbot/tools` - List available tools
- `GET /api/chatbot/guardrails` - Get safety constraints

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

## Styling

Both components use Tailwind CSS with the custom dark theme:
- `bg-brand-surface` - Content background
- `bg-brand-dark` - Page background
- `border-brand-border` - Border color
- `text-gray-100` / `text-gray-300` / `text-gray-500` - Text colors

Adjust class names if your theme differs.

## Environment Variables

Set these in your build environment:

```env
# API base URL (should be proxied by nginx)
VITE_API_BASE_URL=/api
```

## Features

### ChatBot Component

**Message Display:**
- User messages (right-aligned, cyan background)
- Assistant messages (left-aligned, gray background)
- Tool usage indicators showing which tools were executed

**Input:**
- Single-line text input
- Send button with loading state
- Enter key to submit
- Shift+Enter for new line (if multiline is needed)

**Error Handling:**
- Network errors displayed to user
- API key missing errors
- Failed to load history

**Auto-reload:**
- Loads last 50 messages on mount
- Scrolls to latest message on new messages

### AdminPage Component

**Configuration Sections:**

1. **LLM Settings**
   - Provider selection (Anthropic, OpenAI stub)
   - Model name input
   - Enable/disable toggle

2. **System Prompt**
   - Large textarea for custom system prompt
   - Defines chatbot's role and behavior

3. **Tools**
   - Checkbox toggles for each of 5 database tools:
     - query_database
     - get_metrics
     - get_slow_queries
     - get_table_stats
     - check_locks

4. **Safety Guardrails**
   - Write query protection toggle
   - DDL query protection toggle
   - Query timeout setting (1-60 seconds)
   - Max rows per query (100-10000)

**User Actions:**
- Save button persists changes to backend
- Reload button fetches latest config from backend
- Success/error messages show result of operations

## Testing

### Manual Testing

1. **Start the backend:**
   ```bash
   python3 main.py run --config config.yaml
   ```

2. **Build the dashboard:**
   ```bash
   npm run build
   ```

3. **Test ChatBot:**
   - Navigate to dashboard
   - Click on ChatBot panel
   - Ask a question: "How many customers do we have?"
   - Verify response and tool usage

4. **Test AdminPage:**
   - Navigate to /admin
   - Change a setting (e.g., disable a tool)
   - Click "Save Configuration"
   - Verify success message
   - Reload page to confirm persistence

### API Testing

```bash
# Get config
curl -H "Authorization: Bearer <token>" http://localhost:8084/api/chatbot/config

# Send message
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"How many orders exist?"}'

# Get tools
curl -H "Authorization: Bearer <token>" http://localhost:8084/api/chatbot/tools
```

## Deployment

### Prerequisites
- SSH access to arm2 (IP: 10.0.2.11, user: ubuntu)
- www-data ownership of /var/www/dashboard/
- nginx reverse proxy configured

### On arm2 (Frontend Server)

**Full deployment workflow:**

1. **Build locally:**
   ```bash
   cd /home/ubuntu/sql_agent/frontend
   npm run build
   ```

2. **Create temp directory on arm2:**
   ```bash
   ssh ubuntu@10.0.2.11 "mkdir -p /tmp/dashboard-deploy"
   ```

3. **Copy dist files to temp directory:**
   ```bash
   scp -r dist/* ubuntu@10.0.2.11:/tmp/dashboard-deploy/
   ```

4. **Copy to www with proper permissions and cleanup:**
   ```bash
   ssh ubuntu@10.0.2.11 "sudo cp -r /tmp/dashboard-deploy/* /var/www/dashboard/ && \
     sudo chown -R www-data:www-data /var/www/dashboard/ && \
     rm -rf /tmp/dashboard-deploy"
   ```

5. **Reload nginx:**
   ```bash
   ssh ubuntu@10.0.2.11 "sudo nginx -t && sudo systemctl reload nginx"
   ```

6. **Verify deployment:**
   - Clear browser cache
   - Refresh https://sqlagent.dittmar.it
   - Check that updates are visible

**All-in-one deployment command:**
```bash
npm run build && \
  ssh ubuntu@10.0.2.11 "mkdir -p /tmp/dashboard-deploy" && \
  scp -r dist/* ubuntu@10.0.2.11:/tmp/dashboard-deploy/ && \
  ssh ubuntu@10.0.2.11 "sudo cp -r /tmp/dashboard-deploy/* /var/www/dashboard/ && \
    sudo chown -R www-data:www-data /var/www/dashboard/ && \
    rm -rf /tmp/dashboard-deploy && \
    sudo nginx -t && sudo systemctl reload nginx" && \
  echo "✅ Deployment complete"
```

## Environment Variables (Backend)

On arm1 (agent backend), set:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or add to `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
```

## Troubleshooting

**"API key not configured" error:**
- Set `ANTHROPIC_API_KEY` environment variable on backend
- Verify it's set: `echo $ANTHROPIC_API_KEY`

**404 on chatbot endpoints:**
- Ensure backend is running on port 8084
- Check that API endpoints are accessible: `curl http://localhost:8084/api/health`

**Chat messages not loading:**
- Verify JWT token is valid
- Check browser console for CORS errors
- Ensure proxy is configured correctly in vite.config.ts

**Configuration not saving:**
- Check network tab in browser dev tools
- Verify API key is set on backend
- Check backend logs for errors

## Recent Changes (June 2026)

### UI Changes
- **Removed security section from ChatbotInfoBox** — Security scanning (Prisma AIRS) is configured server-side and operates transparently. Users don't need to see scanner status in the UI.
- **Assistant Info Box now shows:** Current LLM model, available tools, admin settings link
- **Deployment:** Successfully deployed to arm2 (10.0.2.11) at /var/www/dashboard/ on June 16, 2026

### Backend Security
- **Prisma AIRS three-stage scanning:** All data exchanges (user prompts, tool outputs, LLM responses) are scanned for threats
- **Fail-closed design:** If Prisma AIRS is unavailable, requests are blocked to prevent silent data leakage
- **Database schema fixes:** System prompt updated with exact table definitions and critical column name notes

### Architecture
See main README.md for detailed info on:
- Three-stage Prisma AIRS security scanning
- Fail-closed threat response design
- Profile name preference for reliability
- Database schema and system prompt

## Future Enhancements

- [ ] Export chat history to CSV
- [ ] Conversation threading
- [ ] Scheduled queries via chatbot
- [ ] Fine-tuned models for database context
- [ ] Multi-user chat sessions
- [ ] Analytics on chatbot usage
- [ ] Security scanning visualization (on-demand, not real-time)
