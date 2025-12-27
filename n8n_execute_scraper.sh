#!/bin/bash
# n8n Execute Scraper Script
# This script can be called from n8n Execute Command node

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the scraper
python3 main.py

# Capture exit code
EXIT_CODE=$?

# Copy output into n8n-allowed directory for Read Binary File
N8N_FILES_DIR="${HOME}/.n8n-files"
OUTPUT_JSON="${SCRIPT_DIR}/output/gumtree_data.json"

mkdir -p "${N8N_FILES_DIR}"
if [ -f "${OUTPUT_JSON}" ]; then
    cp "${OUTPUT_JSON}" "${N8N_FILES_DIR}/gumtree_data.json"
fi

# Return exit code for n8n to check
exit $EXIT_CODE
