# Chatbot Deployment Guide for arm2

This guide explains how to integrate the chatbot components into the existing dashboard on arm2.

## Prerequisites

- arm2 dashboard project with React 18 + TypeScript
- Tailwind CSS configured with dark theme
- axios installed
- App.tsx with routing setup
- Authentication system passing JWT tokens

## Step-by-Step Integration

### 1. Copy Component Files

On arm2, copy the new components:

```bash
# From sql_agent repository on arm1
scp arm1:/home/ubuntu/sql_agent/frontend/src/components/ChatBot.tsx \
    /path/to/dashboard/src/components/

scp arm1:/home/ubuntu/sql_agent/frontend/src/pages/AdminPage.tsx \
    /path/to/dashboard/src/pages/
```

Or if you have git access:
```bash
cd /path/to/dashboard
git pull origin master  # if chatbot files are in version control
```

### 2. Update App.tsx

Add imports and routes:

```tsx
// At the top with other imports
import ChatBot from './components/ChatBot';
import AdminPage from './pages/AdminPage';

// In your router/Routes section, add:
<Route path="/admin" element={<AdminPage />} />

// In your main dashboard grid, add ChatBot component:
<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
  {/* Existing panels */}
  <LocksPanel />
  <PerformancePanel />
  <CapacityPanel />
  
  {/* NEW: Add chatbot panel */}
  <ChatBot />
</div>
```

### 3. Update Header/Navigation

Add link to admin page in Header.tsx or Navigation component:

```tsx
{/* In your navigation menu */}
<Link 
  to="/admin"
  className="px-4 py-2 text-gray-300 hover:text-white rounded-lg hover:bg-gray-700"
>
  ⚙️ Chatbot Config
</Link>

{/* Or as a button */}
<button
  onClick={() => navigate('/admin')}
  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded-lg"
>
  Admin Settings
</button>
```

### 4. Verify API Configuration

Ensure nginx is proxying `/api/*` requests to arm1:8084:

**File: `/etc/nginx/sites-available/dashboard` (on arm2)**

```nginx
server {
    listen 443 ssl http2;
    server_name sqlagent.dittmar.it;

    ssl_certificate /etc/letsencrypt/live/sqlagent.dittmar.it/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sqlagent.dittmar.it/privkey.pem;

    location / {
        root /var/www/dashboard;
        try_files $uri /index.html;
    }

    # API proxy to arm1:8084
    location /api/ {
        proxy_pass http://arm1:8084/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For long-running requests (Claude API)
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;
    }
}
```

Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Install Dependencies (if needed)

```bash
cd /path/to/dashboard
npm install axios  # Make sure axios is installed
```

### 6. Build Dashboard

```bash
npm run build

# Verify build output
ls -la dist/
```

### 7. Deploy to nginx

```bash
# Backup current dashboard
sudo cp -r /var/www/dashboard /var/www/dashboard.backup.$(date +%Y%m%d)

# Copy new build
sudo cp -r dist/* /var/www/dashboard/

# Verify permissions
sudo chown -R www-data:www-data /var/www/dashboard/

# Reload nginx
sudo systemctl reload nginx
```

### 8. Test the Chatbot

1. Open dashboard: https://sqlagent.dittmar.it
2. Login with credentials
3. Verify ChatBot panel appears on dashboard
4. Try asking: "How many customers are in the database?"
5. Click on ⚙️ Admin Settings link
6. Verify AdminPage loads with configuration
7. Toggle a tool and click Save
8. Verify "Configuration saved successfully" message

## Troubleshooting

### ChatBot Component Not Appearing

**Issue:** Component doesn't show on dashboard
**Solution:**
- Check browser console for errors: `F12` → Console tab
- Verify imports in App.tsx are correct
- Check that ChatBot.tsx file exists in src/components/
- Run `npm run build` again

### "Cannot GET /api/chatbot/*"

**Issue:** ChatBot component can't reach API
**Solution:**
- Verify nginx is running: `sudo systemctl status nginx`
- Check nginx config: `sudo nginx -t`
- Verify arm1 is reachable from arm2: `ping 10.0.1.177` (adjust IP)
- Check API is running on arm1: `curl http://10.0.1.177:8084/api/health`
- Review nginx error log: `sudo tail /var/log/nginx/error.log`

### "API key not configured" Error

**Issue:** Chat sends message but gets error
**Solution:**
- On arm1, set ANTHROPIC_API_KEY: `export ANTHROPIC_API_KEY="sk-ant-..."`
- Restart API: `pkill -f "python3 main.py run" && python3 main.py run --config config.yaml`
- Increase nginx proxy timeout for Claude API (see nginx config above)

### Chat Component Shows "Not authorized"

**Issue:** 401 Unauthorized error
**Solution:**
- Verify JWT token is being sent: Check browser Network tab
- Verify token is valid (expiry is 24 hours)
- Check that axios is using correct header: `Authorization: Bearer <token>`
- Re-login and get a fresh token

### AdminPage Shows "Database not available"

**Issue:** Cannot load config
**Solution:**
- Verify arm1 API is running and healthy: `curl http://arm1:8084/api/health`
- Check JWT token is valid
- Review browser console for CORS errors
- Verify `chatbot_config` table exists on arm1

## Performance Tuning

### For Large Chat Histories

If chat loads slowly with many messages:

```tsx
// In ChatBot.tsx, reduce history limit
const loadHistory = async () => {
  const response = await axios.get('/api/chatbot/history?limit=20');  // Reduce from 50
  setMessages(response.data);
};
```

### For Slow Claude API Responses

Increase nginx timeout:

```nginx
location /api/chat {
    proxy_read_timeout 180s;  # 3 minutes for long responses
    proxy_connect_timeout 30s;
}
```

## Monitoring

### Check Chatbot Usage

```bash
# On arm1, query chat history
psql -h localhost -U agent -d agent_store -c \
  "SELECT COUNT(*) as total_messages, \
          COUNT(DISTINCT DATE(created_at)) as days_active \
   FROM chat_messages;"
```

### Monitor API Performance

```bash
# Check response times
curl -v http://localhost:8084/api/chatbot/config

# Watch API logs (if stdout logging)
tail -f /tmp/api.log
```

## Rollback

If issues occur:

```bash
# Restore backup
sudo rm -rf /var/www/dashboard
sudo cp -r /var/www/dashboard.backup.YYYYMMDD /var/www/dashboard

# Reload nginx
sudo systemctl reload nginx
```

## Verification Checklist

- [ ] ChatBot.tsx copied to src/components/
- [ ] AdminPage.tsx copied to src/pages/
- [ ] App.tsx updated with imports and routes
- [ ] Header/Navigation has link to admin page
- [ ] npm dependencies installed (axios)
- [ ] Build completed successfully
- [ ] Dashboard deployed to /var/www/dashboard
- [ ] nginx config proxies /api/* to arm1:8084
- [ ] nginx reload without errors
- [ ] Dashboard loads in browser
- [ ] Login works
- [ ] ChatBot panel visible on dashboard
- [ ] AdminPage loads when clicking admin link
- [ ] Test chat message (if ANTHROPIC_API_KEY set)
- [ ] Configuration can be updated in AdminPage

## Support

For issues with the chatbot implementation:

1. Check logs on arm1:
   ```bash
   python3 scripts/test_chatbot.py
   ```

2. Review implementation guide:
   ```bash
   cat CHATBOT_IMPLEMENTATION.md
   ```

3. Check frontend README:
   ```bash
   cat frontend/README.md
   ```
