# n8n Workflow Sharing Guide

This guide explains how someone else can import and run the Gumtree Scraper n8n
workflow on their machine.

## What they need

- Node.js installed (so they can run `npx n8n`).
- Python 3.8+.
- This project folder on disk.
- Valid Scrapfly API key and Gumtree credentials in `config.py`.

## Setup steps

1) Open a terminal and go to the project folder:
```bash
cd /path/to/Salaheddine\ Mokhtari
```

2) Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3) Make sure the runner script is executable:
```bash
chmod +x n8n_execute_scraper.sh
```

4) Start n8n with Execute Command enabled:
```bash
NODES_EXCLUDE='[]' npx n8n
```

5) In the browser, open:
```
http://localhost:5678
```

6) Import the workflow:
- Workflows -> Import from File
- Select `Gumtree Scraper Automation.json`

7) Verify key node settings:
- Execute Scraper
  - Command: `./n8n_execute_scraper.sh`
  - Working Directory: `/path/to/Salaheddine Mokhtari`
- Read JSON Output
  - File Path: `/Users/<user>/.n8n-files/gumtree_data.json`
- Log Results / Log Error
  - File Name: `/Users/<user>/.n8n-files/scraper_log_{{...}}.txt`

8) Run the workflow manually to test.

## Notes about file access

n8n v2 only allows file access under `~/.n8n-files` by default. The script
copies the JSON output to that folder, so the workflow reads and writes there.

If they want to allow the project folder directly, start n8n like this:
```bash
NODES_EXCLUDE='[]' N8N_FILE_ALLOWED_PATHS="$HOME/.n8n-files,/path/to/Salaheddine Mokhtari" npx n8n
```

## Common issues

- "Unrecognized node type: executeCommand"
  - Start n8n with `NODES_EXCLUDE='[]'`.

- "Access to the file is not allowed"
  - Use the default `~/.n8n-files` paths or set `N8N_FILE_ALLOWED_PATHS`.

- "Command failed: No such file or directory"
  - Check `Execute Scraper` command and working directory.
  - Make sure `n8n_execute_scraper.sh` is executable.
