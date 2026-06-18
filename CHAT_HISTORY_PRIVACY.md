# Chat History Privacy - Per-User Implementation

## Overview

Chat history is now **private per user**. Each user only sees their own chat messages, preventing information disclosure between users.

## Changes Made (June 17, 2026)

### Database Schema
- Added `username` column to `chat_messages` table
- Existing messages from before this update have `username = NULL`
- New messages include the username of who sent them

### API Changes

**POST /api/chatbot/chat**
- Now stores the current user's username with each message
- Messages are linked to the authenticated user who sent them

**GET /api/chatbot/history**
- Now filters messages to show ONLY the current user's messages
- Users cannot see other users' chat history
- Old messages without username are not shown (treated as unknown user)

**DELETE /api/chatbot/history**
- Now deletes ONLY the current user's messages
- Users cannot delete other users' messages
- Returns "Your chat history cleared" to clarify scope

### Files Modified
- `store/chatbot_models.py` — Added `username` field to ChatMessage model
- `api/server.py` — Updated chat, history, and clear endpoints to use username

## Security Implications

### Before This Change ❌
```
User A sends: "Select all credit cards from customers"
↓
Message stored WITHOUT user information
↓
User B queries /api/chatbot/history
↓
User B sees User A's message AND the credit card results
```

### After This Change ✅
```
User A sends: "Select all credit cards from customers"
↓
Message stored WITH username='user_a'
↓
User B queries /api/chatbot/history
↓
User B sees ONLY their own messages
↓
User A's message is hidden from User B
```

## How It Works

### Chat Storage
When a user sends a message through the chatbot interface:
1. Request is authenticated (JWT token verified)
2. Username is extracted from the token
3. Message is saved with the username
4. Only that user can retrieve the message later

### Chat Retrieval
When a user requests chat history:
1. Request is authenticated
2. Username is extracted from the token
3. Only messages WHERE `username == current_user` are returned
4. All other messages are hidden

### Chat Deletion
When a user clears their chat history:
1. Request is authenticated
2. Only messages WHERE `username == current_user` are deleted
3. Other users' messages are unaffected

## Testing User-Private History

### Test Scenario: Two Users

**User 1: admin**
```bash
# Get token for admin
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"PASSWORD"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Send message as admin
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Show me admin data"}'

# Check history (should show 1 message)
curl -H "Authorization: Bearer $TOKEN_ADMIN" \
  http://localhost:8084/api/chatbot/history
```

**User 2: testuser**
```bash
# Get token for testuser
TOKEN_USER=$(curl -s -X POST http://localhost:8084/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"PASSWORD"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Send message as testuser
curl -X POST http://localhost:8084/api/chatbot/chat \
  -H "Authorization: Bearer $TOKEN_USER" \
  -H "Content-Type: application/json" \
  -d '{"message":"Show me user data"}'

# Check history (should show 1 message - only their own)
curl -H "Authorization: Bearer $TOKEN_USER" \
  http://localhost:8084/api/chatbot/history
```

**Key Result:** 
- Admin's history shows only: "Show me admin data"
- User's history shows only: "Show me user data"
- Neither can see the other's messages ✓

## Data Structure

### Database Schema
```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY,
    username VARCHAR(255),  -- NEW: Which user sent this
    user_message TEXT NOT NULL,
    assistant_message TEXT,
    tools_used JSON,
    tool_outputs JSON,
    prisma_airs_user_safe BOOLEAN,
    prisma_airs_response_safe BOOLEAN,
    created_at TIMESTAMP WITH TIMEZONE
);
```

### API Response Example
```json
{
  "id": 1,
  "username": "admin",
  "user_message": "Show me customers",
  "assistant_message": "Here are the customers...",
  "tools_used": ["query_database"],
  "created_at": "2026-06-17T12:55:00+00:00"
}
```

## Backward Compatibility

### Old Messages (Before This Update)
- Messages sent before this update have `username = NULL`
- These messages are NOT returned in history (treated as orphaned)
- To include them, run an admin script to assign a default user (optional)

### Migration for Existing Data
If you want to attribute old messages to users:

```python
from store.chatbot_models import ChatMessage
from store import get_session, get_engine

engine = get_engine(config)
session = get_session(engine)

# Option 1: Assign all old messages to admin
session.query(ChatMessage).filter(ChatMessage.username == None).update(
    {"username": "admin"}, synchronize_session=False
)

# Option 2: Delete old messages
session.query(ChatMessage).filter(ChatMessage.username == None).delete()

session.commit()
```

## Admin Access (Future Feature)

Currently, there is no "view all users' history" feature for admins. This could be added with:

```python
# Optional admin endpoint
@app.get("/api/admin/chatbot/history-all")
def admin_view_all_chat_history(username: str = Depends(verify_token)):
    """Admin-only: view all users' chat history."""
    # Check if user has admin role
    # Return all messages (not filtered by username)
```

This would require:
1. Admin role verification
2. Audit logging of who accessed whose history
3. Clear UI indicators that you're viewing someone else's data

## Audit Trail

Each message now includes:
- Who sent it (`username`)
- What they asked (`user_message`)
- What the assistant responded (`assistant_message`)
- Which tools were used (`tools_used`)
- Security scan results (`prisma_airs_user_safe`, `prisma_airs_response_safe`)
- When it was sent (`created_at`)

This creates an audit trail for compliance and security investigations.

## Future Enhancements

- [ ] Admin endpoint to view any user's history (with audit logging)
- [ ] Export chat history (PDF, CSV) for users
- [ ] Archive old messages (> 90 days) separately
- [ ] Search within own chat history
- [ ] Message reactions/ratings for feedback
- [ ] Conversation bookmarking and sharing with selected users

## Troubleshooting

**Issue:** "I see other users' messages in my history"
- Old messages from before this update have `username = NULL` (they're hidden)
- Restart the API to pick up schema changes: `bash start_api.sh`
- Clear browser cache and refresh

**Issue:** "Message not saving with username"
- Check API logs: `tail -f api.log`
- Verify JWT token is valid
- Ensure API is running latest version

---

**Implemented:** June 17, 2026  
**Version:** 1.0
