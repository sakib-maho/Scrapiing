#!/bin/bash
# Quick start script for local backend

echo "🚀 Starting Gumtree Scraper API Server for n8n.cloud"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found!"
    echo "Please create one first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check and install Flask if needed
echo "📦 Checking dependencies..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask and dependencies..."
    pip install flask flask-cors
fi

echo ""
echo "✅ Dependencies ready!"
echo ""
echo "🌐 Starting API server..."
echo "   Local URL: http://localhost:5001"
echo "   Health check: http://localhost:5001/health"
echo "   Scrape endpoint: http://localhost:5001/scrape"
echo ""
echo "📝 Next steps:"
echo "   1. Keep this terminal open (server must keep running)"
echo "   2. Open a NEW terminal and run: ngrok http 5001"
echo "   3. Copy the ngrok HTTPS URL (e.g., https://abc123.ngrok.io)"
echo "   4. Update n8n.cloud workflow with that URL"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

python3 api_server.py

