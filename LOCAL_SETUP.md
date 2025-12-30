# Local Backend Setup for n8n.cloud

This guide will help you run the API server on your local computer and connect it to n8n.cloud.

## Step 1: Install Dependencies

Open a terminal and run:

```bash
cd "/Users/sakib/Salaheddine Mokhtari"
source venv/bin/activate
pip install flask flask-cors
```

Or use the startup script (it will auto-install):

```bash
./start_api_server.sh
```

## Step 2: Start the API Server

Run the startup script:

```bash
./start_api_server.sh
```

**OR** manually:

```bash
source venv/bin/activate
python3 api_server.py
```

You should see:
```
Starting Gumtree Scraper API server on 0.0.0.0:5000
Health check: http://0.0.0.0:5000/health
Scrape endpoint: http://0.0.0.0:5000/scrape
```

**Keep this terminal open!** The server needs to keep running.

## Step 3: Test the Server Locally

Open a new terminal and test:

```bash
# Health check
curl http://localhost:5001/health

# Test scraping (this will actually run the scraper!)
curl -X POST http://localhost:5001/scrape \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 1, "max_listings": 2}'
```

## Step 4: Make It Accessible to n8n.cloud

n8n.cloud needs to reach your local server. You have two options:

### Option A: Use ngrok (Recommended - Free & Easy)

1. **Install ngrok:**
   - Download from: https://ngrok.com/download
   - Or install via Homebrew: `brew install ngrok`

2. **Start ngrok** (in a new terminal, keep API server running):
   ```bash
   ngrok http 5001
   ```

3. **Copy the HTTPS URL** ngrok gives you:
   - Example: `https://abc123.ngrok.io`
   - This is your public URL that n8n.cloud can access

4. **Update n8n workflow:**
   - Go to https://sakib162.app.n8n.cloud/home/workflows
   - Open your workflow
   - Click "Call Scraper API" node
   - Change URL to: `https://abc123.ngrok.io/scrape` (use YOUR ngrok URL)
   - Save

### Option B: Use localtunnel (Alternative Free Option)

1. **Install:**
   ```bash
   npm install -g localtunnel
   ```

2. **Start tunnel:**
   ```bash
   lt --port 5000
   ```

3. **Use the URL it gives you** in your n8n workflow

## Step 5: Test from n8n.cloud

1. Go to your n8n.cloud workflow
2. Click "Execute Workflow"
3. Check the results!

## Important Notes

⚠️ **Your computer must be on** for n8n.cloud to reach your API server

⚠️ **ngrok URLs change** each time you restart ngrok (unless you have a paid plan)

⚠️ **Keep both terminals open:**
   - Terminal 1: API server (`./start_api_server.sh`)
   - Terminal 2: ngrok (`ngrok http 5001`)

## Troubleshooting

### "Connection refused" in n8n
- Make sure API server is running (Terminal 1)
- Make sure ngrok is running (Terminal 2)
- Check the URL in n8n workflow matches ngrok URL

### "Module not found" error
- Make sure virtual environment is activated: `source venv/bin/activate`
- Install dependencies: `pip install flask flask-cors`

### Port 5001 already in use
- Change port in `api_server.py`: `port = int(os.environ.get('PORT', 8000))`
- Update ngrok: `ngrok http 8000`

### ngrok shows "Tunnel not found"
- Restart ngrok
- Make sure API server is running on port 5000
- Check firewall settings

## Quick Start Commands

```bash
# Terminal 1: Start API server
cd "/Users/sakib/Salaheddine Mokhtari"
source venv/bin/activate
pip install flask flask-cors  # Only needed first time
python3 api_server.py

# Terminal 2: Start ngrok
ngrok http 5001
```

Then use the ngrok HTTPS URL in your n8n.cloud workflow!

