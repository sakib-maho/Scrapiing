#!/bin/bash
# Start the Gumtree Scraper API Server for n8n.cloud

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Please create one first."
    exit 1
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask dependencies..."
    pip install flask flask-cors
fi

# Start the API server
echo "Starting Gumtree Scraper API Server..."
echo "Server will be available at: http://localhost:5001"
echo "Health check: http://localhost:5001/health"
echo "Scrape endpoint: http://localhost:5001/scrape"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 api_server.py

