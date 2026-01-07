# Frontend Configuration

## config.js - Backend API URL Configuration

This file contains the backend API URL used by the frontend application.

### Local Development
For local development, the app automatically detects localhost and uses `/api` as the base URL.

### Production Deployment
**Before deploying to production (Render, Netlify, etc.), you MUST update this file:**

1. Open `config.js`
2. Replace the URL with your actual backend server URL:
   ```javascript
   window.BACKEND_URL = 'https://your-backend-name.onrender.com/api';
   ```
3. Commit and push the changes:
   ```bash
   git add frontend/config.js
   git commit -m "Update backend URL for production"
   git push origin main
   ```

### Current Configuration
The current backend URL is set to:
```
https://collectflow-ai-powered-dca-management-ls10.onrender.com/api
```

### Troubleshooting
If you see errors like:
- `net::ERR_CONNECTION_CLOSED`
- `Failed to fetch`
- `CORS errors`

Check that:
1. ✅ The backend URL in `config.js` is correct
2. ✅ The backend server is running and accessible
3. ✅ The URL includes `/api` at the end
4. ✅ You've committed and pushed the changes
5. ✅ You've redeployed the frontend after making changes

### File Structure
```
frontend/
├── config.js          ← Configure backend URL here
├── index.html         ← Loads config.js
├── dashboard.html     ← Loads config.js
├── dca_portal.html    ← Loads config.js
└── assets/
    └── js/
        └── api.js     ← Uses window.BACKEND_URL
```

### How It Works
1. `config.js` sets `window.BACKEND_URL` globally
2. All HTML files load `config.js` before `api.js`
3. `api.js` checks for `window.BACKEND_URL` and uses it if available
4. This allows easy configuration without modifying core JS files
