# n8n.cloud Setup Guide

This guide explains how to use the Gumtree Scraper with **n8n.cloud** (hosted n8n).

## Important: n8n.cloud Limitations

**n8n.cloud does NOT support the Execute Command node** due to security restrictions. Therefore, we need to run the Python scraper as a web API that n8n.cloud can call via HTTP requests.

## Architecture

```
n8n.cloud → HTTP Request → Flask API Server (your machine) → Python Scraper
```

## Setup Steps

### 1. Install Flask Dependencies

```bash
cd "/Users/sakib/Salaheddine Mokhtari"
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the API Server

Run the Flask API server on your local machine:

```bash
python api_server.py
```

The server will start on `http://0.0.0.0:5000` (or `http://localhost:5000`).

**Test the server:**
```bash
curl http://localhost:5000/health
```

### 3. Make Your Server Accessible to n8n.cloud

n8n.cloud needs to reach your local server. You have two options:

#### Option A: Use ngrok (Recommended for Testing)

1. Install ngrok: https://ngrok.com/download
2. Start your API server: `python api_server.py`
3. In another terminal, expose it:
   ```bash
   ngrok http 5000
   ```
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

#### Option B: Deploy to a Server

Deploy `api_server.py` to a cloud server (AWS, DigitalOcean, Heroku, etc.) that's publicly accessible.

### 4. Import Workflow to n8n.cloud

1. Go to https://sakib162.app.n8n.cloud/home/workflows
2. Click **"Import from File"**
3. Select `Gumtree Scraper Automation - n8n.cloud.json`
4. Open the workflow editor

### 5. Configure the HTTP Request Node

1. Click on the **"Call Scraper API"** node
2. Update the URL:
   - If using ngrok: `https://YOUR_NGROK_URL.ngrok.io/scrape`
   - If using a server: `http://YOUR_SERVER_IP:5000/scrape`
3. Configure parameters (optional):
   - `category_url`: Gumtree category path
   - `max_pages`: Maximum pages to scrape
   - `max_listings`: Maximum listings to scrape
   - `location`: Location filter (optional)
   - `save_to_sheets`: Whether to save to Google Sheets (true/false)

### 6. Test the Workflow

1. Click **"Execute Workflow"** in n8n
2. Check the results in the workflow execution

## API Endpoints

### POST /scrape

Main scraping endpoint. Accepts JSON:

```json
{
  "category_url": "s-farming-veterinary/nsw/c21210l3008839",
  "max_pages": 1,
  "max_listings": 5,
  "location": "",
  "save_to_sheets": true
}
```

### GET /scrape

Simple GET endpoint with query parameters:
```
http://localhost:5000/scrape?category_url=s-farming-veterinary/nsw/c21210l3008839&max_pages=1&max_listings=5
```

### GET /health

Health check endpoint:
```
http://localhost:5000/health
```

## Response Format

### Success Response:
```json
{
  "success": true,
  "listings_count": 5,
  "listings": [...],
  "scraped_at": "2024-01-01T12:00:00",
  "google_sheets_saved": true,
  "statistics": {...},
  "metadata": {...}
}
```

### Error Response:
```json
{
  "success": false,
  "error": "Error message",
  "traceback": "..."
}
```

## Running the Server in Production

For production use, consider:

1. **Use a production WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
   ```

2. **Add authentication** to the API (API keys, tokens, etc.)

3. **Use HTTPS** (required for production)

4. **Set up monitoring** and logging

## Troubleshooting

### "Connection refused" in n8n.cloud
- Make sure your API server is running
- Check that ngrok is running (if using ngrok)
- Verify the URL in the HTTP Request node

### "Timeout" errors
- Scraping can take time. Consider increasing timeout in HTTP Request node options

### API server not starting
- Check that Flask is installed: `pip install flask flask-cors`
- Check port 5000 is not in use: `lsof -i :5000`

## Security Notes

⚠️ **Important:** The current API has no authentication. Anyone with the URL can trigger scraping.

For production, add:
- API key authentication
- Rate limiting
- HTTPS only
- IP whitelisting (if possible)

