# Chatbot Integration Implementation Guide

## What's Been Implemented

### 1. Data Generation ✓
- Sample data exists in shopdb (500 customers, 2000+ orders from pgbench)
- Products table with 50+ items across categories
- Ready for chatbot queries

### 2. Backend Infrastructure ✓
- **store/chatbot_models.py**: Database models for chatbot config and chat history
- **orchestrator/chatbot_service.py**: Service handling Claude API integration
- **requirements.txt**: Added anthropic==0.27.0

### 3. Chatbot Features Implemented
- **LLM Integration**: Anthropic Claude API (extensible for other providers)
- **Tool System**: 5 database tools
  - `query_database`: Execute SELECT queries safely
  - `get_metrics`: Current DB metrics
  - `get_slow_queries`: Performance insights
  - `get_table_stats`: Table information
  - `check_locks`: Lock detection
- **Guardrails**: 
  - Write protection (SELECT only)
  - DDL prevention
  - Query timeouts
  - Row limits
  - Configurable restrictions

## What Needs to Be Completed

### Backend (API Endpoints)

**File: api/server.py**

Add these endpoints:

```python
@app.get("/api/chatbot/config")
def get_chatbot_config(_: str = Depends(verify_token)):
    """Get current chatbot configuration."""
    from store.chatbot_models import ChatbotConfig
    session = _state.get("session_factory")()
    config = session.query(ChatbotConfig).first()
    return config.to_dict() if config else {"error": "Not configured"}

@app.post("/api/chatbot/config")
def update_chatbot_config(config_update: dict, _: str = Depends(verify_token)):
    """Update chatbot configuration (admin only)."""
    from store.chatbot_models import ChatbotConfig
    session = _state.get("session_factory")()
    config = session.query(ChatbotConfig).first() or ChatbotConfig()
    for key, value in config_update.items():
        if hasattr(config, key):
            setattr(config, key, value)
    session.add(config)
    session.commit()
    return {"success": True}

@app.post("/api/chatbot/chat")
def chat_with_bot(message: dict, _: str = Depends(verify_token)):
    """Send a message to the chatbot."""
    from store.chatbot_models import ChatbotConfig, ChatMessage
    from orchestrator.chatbot_service import ChatbotService
    
    session = _state.get("session_factory")()
    config = session.query(ChatbotConfig).first()
    
    service = ChatbotService(config.to_dict() if config else {}, db_config)
    response = service.chat(message.get("message", ""))
    
    # Store in history
    msg = ChatMessage(
        user_message=message.get("message", ""),
        assistant_message=response.get("assistant_message", ""),
        tools_used=response.get("tools_used", [])
    )
    session.add(msg)
    session.commit()
    
    return response

@app.get("/api/chatbot/history")
def get_chat_history(limit: int = 50, _: str = Depends(verify_token)):
    """Get chat message history."""
    from store.chatbot_models import ChatMessage
    session = _state.get("session_factory")()
    messages = session.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    return [msg.to_dict() for msg in reversed(messages)]

@app.get("/api/chatbot/tools")
def get_available_tools(_: str = Depends(verify_token)):
    """Get list of available tools."""
    from orchestrator.chatbot_service import AVAILABLE_TOOLS
    return AVAILABLE_TOOLS

@app.get("/api/chatbot/guardrails")
def get_guardrails(_: str = Depends(verify_token)):
    """Get current safety guardrails."""
    from orchestrator.chatbot_service import DEFAULT_GUARDRAILS
    session = _state.get("session_factory")()
    config = session.query(ChatbotConfig).first()
    return config.guardrails if config else DEFAULT_GUARDRAILS
```

### Frontend Components

**File: src/components/ChatBot.tsx**

```typescript
import React, { useState, useEffect, useRef } from 'react';

interface Message {
  user_message: string;
  assistant_message: string;
  tools_used: string[];
  created_at: string;
}

export default function ChatBot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/chatbot/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: input }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessages((prev) => [
          ...prev,
          {
            user_message: input,
            assistant_message: data.assistant_message,
            tools_used: data.tools_used || [],
            created_at: new Date().toISOString(),
          },
        ]);
        setInput('');
      }
    } catch (err) {
      console.error('Chat error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-brand-surface border border-brand-border rounded-xl">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className="space-y-2">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-cyan-900/40 text-cyan-100 px-4 py-2 rounded-lg max-w-md">
                {msg.user_message}
              </div>
            </div>
            {/* Assistant message */}
            <div className="flex justify-start">
              <div className="bg-gray-800/50 text-gray-100 px-4 py-2 rounded-lg max-w-md">
                {msg.assistant_message}
                {msg.tools_used.length > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    Tools: {msg.tools_used.join(', ')}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-700 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            disabled={loading}
            placeholder="Ask about the database..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-500"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg disabled:opacity-50 font-semibold"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
```

**File: src/pages/AdminPage.tsx**

Admin dashboard for configuring:
- LLM model and provider selection
- API key management
- System prompt editing
- Tool enable/disable
- Guardrail configuration
- Chat history management

## Setup Steps

### 1. Install Dependencies
```bash
cd ~/sql_agent
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize Chatbot Config
```sql
INSERT INTO chatbot_config (llm_provider, llm_model, system_prompt, tools, guardrails, enabled)
VALUES ('anthropic', 'claude-3-5-sonnet-20241022', '...', '[...]', '{...}', true);
```

### 3. Set Anthropic API Key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Add Components to Dashboard
- Import ChatBot.tsx in App.tsx
- Add admin page route
- Display chat panel on dashboard

## Configuration Example

```yaml
chatbot:
  llm_provider: "anthropic"
  llm_model: "claude-3-5-sonnet-20241022"
  system_prompt: |
    You are a database monitoring assistant...
  tools:
    - query_database
    - get_metrics
    - get_slow_queries
    - get_table_stats
    - check_locks
  guardrails:
    allow_writes: false
    allow_ddl: false
    query_timeout_seconds: 5
    max_rows_return: 1000
    restricted_tables: []
```

## Security Notes

1. **API Keys**: Store in environment variables or secrets management system, never in config files
2. **Query Safety**: Chatbot service enforces guardrails on all queries
3. **Authorization**: Chatbot access requires JWT authentication
4. **Audit**: All chat interactions stored in `chat_messages` table with timestamps
5. **Tool Restrictions**: Admin can disable tools as needed

## Future Enhancements

- [ ] Support for other LLM providers (OpenAI, custom gateways)
- [ ] Fine-tuned models for database-specific tasks
- [ ] Conversation context persistence
- [ ] Scheduled queries and alerts via chatbot
- [ ] Integration with HITL approval queue
- [ ] Chat analytics and usage metrics
