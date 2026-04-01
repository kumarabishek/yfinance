# Yahoo Finance MCP Server — Remote Edition

Your existing yfinance MCP server, upgraded to run as a remote HTTP service so it works on **Claude iOS**, **claude.ai**, and **Claude Desktop** — all from a single deployment.

## What Changed from Your Local Version

Only **2 things** changed from your original stdio server:

1. **`stateless_http=True`** added to the FastMCP constructor (enables remote mode)
2. **`mcp.run(transport="streamable-http")`** instead of `mcp.run()` (switches from stdio to HTTP)

All 10 tools are identical to your working local version.

---

## Quick Start (Local Testing)

```bash
cd yfinance-mcp-remote
uv sync
uv run server.py
```

Server starts at `http://localhost:8000`. Test it with the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
# Enter URL: http://localhost:8000/mcp
```

---

## Deployment Options

### Option A: Railway (Easiest — Free Tier Available)

1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app), create new project → "Deploy from GitHub"
3. Railway auto-detects the Dockerfile
4. Once deployed, you get a URL like `https://yfinance-mcp-production-xxxx.up.railway.app`
5. Your MCP endpoint is: `https://your-app.up.railway.app/mcp`

### Option B: Render (Free Tier Available)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service → connect repo
3. Set: Environment = Docker, Free instance
4. Deploy. Your endpoint: `https://your-app.onrender.com/mcp`

Note: Free tier spins down after inactivity — first request after sleep takes ~30s.

### Option C: Fly.io

```bash
# Install flyctl, then:
cd yfinance-mcp-remote
fly launch          # Follow prompts, pick a region near you (sjc for SF)
fly deploy
```

Your endpoint: `https://your-app.fly.dev/mcp`

### Option D: Cloudflare Tunnel (Run from Home, No Cloud Costs)

Keep the server running on your Mac and expose it to the internet:

```bash
# Install cloudflared
brew install cloudflared

# Start your server
uv run server.py &

# Create a tunnel (first time: will prompt for Cloudflare login)
cloudflared tunnel --url http://localhost:8000
```

Gives you a URL like `https://xxxx-xxxx.trycloudflare.com`. Your MCP endpoint: `https://xxxx.trycloudflare.com/mcp`

For a permanent named tunnel:
```bash
cloudflared tunnel create yfinance-mcp
cloudflared tunnel route dns yfinance-mcp yfinance-mcp.yourdomain.com
cloudflared tunnel run yfinance-mcp
```

### Option E: ngrok (Quick Testing)

```bash
uv run server.py &
ngrok http 8000
```

Your endpoint: `https://xxxx.ngrok-free.app/mcp`

---

## Connecting to Claude iOS

Once your server is deployed and you have the URL:

1. Open **claude.ai** in your browser (NOT the mobile app — you can't add connectors from mobile)
2. Go to **Settings → Connectors**
3. Click **"Add custom connector"**
4. Enter your MCP server URL (e.g., `https://your-app.railway.app/mcp`)
5. Click **Add**

That's it — the connector automatically syncs to your Claude iOS app. Open Claude on your iPhone, start a new chat, and ask "get me a quote on COHR" — it'll use your yfinance server.

---

## Keeping Your Local Server Too

You can run BOTH versions simultaneously:

- **Local stdio** → Claude Desktop (via `claude_desktop_config.json`)
- **Remote HTTP** → Claude iOS + claude.ai (via Settings → Connectors)

They're independent. The local version is faster for desktop use; the remote version enables mobile.

---

## Notes

- No auth required for personal use — your server is "authless"
- If deploying publicly, consider adding a simple API key check (see server.py comments)
- Yahoo Finance data is free but rate-limited — avoid hammering with rapid calls
- Streamable HTTP is the recommended transport going forward (SSE is being deprecated)
- The `stateless_http=True` flag means no session state between requests, which is ideal for serverless/container deployments
