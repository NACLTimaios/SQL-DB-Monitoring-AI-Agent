# Chatbot Deployment to arm2 Dashboard

## Quick Start

```bash
# From your local machine or arm2
scp arm1:/home/ubuntu/sql_agent/frontend/src/components/ChatBot.tsx \
    arm2:/path/to/dashboard/src/components/

scp arm1:/home/ubuntu/sql_agent/frontend/src/pages/AdminPage.tsx \
    arm2:/path/to/dashboard/src/pages/
```

## Step-by-Step Deployment

### 1. Copy Component Files

On arm2, create the directories if they don't exist:

```bash
mkdir -p /path/to/dashboard/src/components
mkdir -p /path/to/dashboard/src/pages
```

Copy the files:

```bash
# ChatBot component
cp ChatBot.tsx src/components/

# Admin page component  
cp AdminPage.tsx src/pages/
```

### 2. Update App.tsx

Open `src/App.tsx` and add imports at the top:

```tsx
import ChatBot from './components/ChatBot';
import AdminPage from './pages/AdminPage';
```

Add route for admin page (within your Router/Routes):

```tsx
<Route path="/admin" element={<AdminPage />} />
```

Add ChatBot component to your dashboard grid/layout. For example, in your main dashboard section:

```tsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
  {/* Existing panels */}
  <LocksPanel />
  <PerformancePanel />
  <CapacityPanel />
  
  {/* NEW: Add this line */}
  <ChatBot />
</div>
```

### 3. Update Navigation (Optional)

Add a link to the admin page in your Header/Navigation component:

```tsx
// In Header.tsx or similar
<Link 
  to="/admin"
  className="px-4 py-2 text-gray-300 hover:text-white rounded-lg hover:bg-gray-700"
>
  ⚙️ Chatbot Config
</Link>
```

Or as a button:

```tsx
<button
  onClick={() => navigate('/admin')}
  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded-lg"
>
  Admin Settings
</button>
```

### 4. Verify Dependencies

Ensure axios is installed:

```bash
npm install axios
```

It should already be installed, but verify in `package.json`.

### 5. Build Dashboard

```bash
npm run build
```

Verify the build completes without errors.

### 6. Deploy to Nginx

```bash
# Backup current dashboard
sudo cp -r /var/www/dashboard /var/www/dashboard.backup.$(date +%Y%m%d)

# Deploy new build
sudo cp -r dist/* /var/www/dashboard/

# Fix permissions
sudo chown -R www-data:www-data /var/www/dashboard/

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 7. Verify Deployment

1. Open dashboard in browser: `https://sqlagent.dittmar.it`
2. Login with credentials
3. Verify ChatBot panel appears on dashboard
4. Click on admin link and verify AdminPage loads
5. Try sending a chat message
6. Verify you can change provider settings in AdminPage

## Troubleshooting

### ChatBot component not appearing

**Issue:** Component doesn't show on dashboard

**Solutions:**
- Check browser console (F12) for errors
- Verify imports in App.tsx are correct
- Run `npm run build` again
- Clear browser cache

### "Cannot GET /api/*" errors

**Issue:** API calls failing with 404

**Solutions:**
- Verify nginx is proxying /api to arm1:8084
- Check /etc/nginx/sites-available/dashboard has:
  ```nginx
  location /api/ {
      proxy_pass http://arm1:8084/api/;
  }
  ```
- Reload nginx: `sudo systemctl reload nginx`

### Chatbot responds with errors

**Issue:** "API key not configured" error

**Solutions:**
- On arm1, ensure GOOGLE_API_KEY is set before starting API
- Start API with: `export $(cat .env) && python3 main.py run --config config.yaml`
- Or use: `./start_api.sh`

### Provider switch doesn't work

**Issue:** Can't change providers in AdminPage

**Solutions:**
- Check JWT token hasn't expired (24-hour expiry)
- Check browser network tab for POST errors
- Verify backend API is running and healthy

## Testing Checklist

- [ ] Dashboard loads without errors
- [ ] ChatBot panel visible on dashboard
- [ ] Can send chat messages
- [ ] AdminPage link works
- [ ] AdminPage loads without errors
- [ ] Can change LLM provider dropdown
- [ ] Can change model name
- [ ] Can toggle tools
- [ ] Can adjust guardrails
- [ ] Save button works (no errors)
- [ ] Configuration persists after reload
- [ ] Chat history loads

## Rollback

If deployment fails:

```bash
# Restore backup
sudo rm -rf /var/www/dashboard
sudo mv /var/www/dashboard.backup.YYYYMMDD /var/www/dashboard

# Fix permissions
sudo chown -R www-data:www-data /var/www/dashboard

# Reload nginx
sudo systemctl reload nginx
```

## Component Integration Details

### ChatBot.tsx

**Props:** None (fetches config from API)

**Requires:**
- JWT token in localStorage
- /api/chatbot/* endpoints accessible
- Axios library

**Features:**
- Auto-loads chat history
- Real-time message sending
- Tool usage display
- Error handling

### AdminPage.tsx

**Props:** None (fetches config from API)

**Requires:**
- JWT token in localStorage
- /api/chatbot/config endpoint
- /api/chatbot/tools endpoint  
- Axios library

**Features:**
- Provider/model selection
- System prompt editing
- Tool toggles
- Guardrails configuration
- Real-time save feedback

## API Requirements

These endpoints must be accessible from arm2:

```
GET  /api/chatbot/config
POST /api/chatbot/config
POST /api/chatbot/chat
GET  /api/chatbot/history
GET  /api/chatbot/tools
GET  /api/chatbot/guardrails
```

All require JWT bearer token authentication.

## nginx Configuration Example

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

    # API proxy
    location /api/ {
        proxy_pass http://arm1:8084/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For long-running chatbot requests
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;
    }
}
```

## File Locations

After deployment, your directory structure should look like:

```
dashboard/
├── src/
│   ├── components/
│   │   ├── ChatBot.tsx         ← NEW
│   │   ├── Header.tsx
│   │   └── ...other components
│   ├── pages/
│   │   ├── AdminPage.tsx       ← NEW
│   │   └── ...other pages
│   ├── App.tsx                 [MODIFIED]
│   └── ...other files
├── package.json
├── vite.config.ts
└── ...other files
```

## Next Steps

1. ✅ Deploy components to arm2
2. ✅ Update App.tsx
3. ✅ Build and deploy
4. ✅ Test in browser
5. Users can now:
   - Chat with the database
   - Switch between Anthropic/Google/OpenAI providers
   - Configure chatbot settings
   - View chat history

## Support

See documentation:
- **CHATBOT_IMPLEMENTATION.md** - Full technical details
- **GOOGLE_GEMINI_SETUP.md** - Google Gemini specific setup
- **LLM_PROVIDER_SETUP.md** - All provider setup guides
- **frontend/README.md** - Component technical docs
