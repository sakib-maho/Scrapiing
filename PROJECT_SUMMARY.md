# Project Summary

## Overview
Gumtree Scraping Automation for Australian listings with Google Sheets integration and n8n workflow support.

## Core Files

### Python Scripts
- **`main.py`**: Main execution script (uses environment variables with fallbacks)
- **`api_server.py`**: Flask API server for Railway/n8n.cloud deployment
- **`gumtree_scraper.py`**: Main scraper class with all extraction logic
- **`scrapfly_client.py`**: Scrapfly API client wrapper
- **`data_handler.py`**: Data export and Google Sheets integration
- **`config.py`**: Configuration settings (API keys, URLs, etc.)

### Configuration Files
- **`requirements.txt`**: Python dependencies
- **`Procfile`**: Railway deployment configuration (gunicorn server)
- **`runtime.txt`**: Python runtime version for Railway
- **`railway.json`**: Railway project configuration
- **`credentials.json`**: Google OAuth2 credentials (not in repo, user must add)
- **`token.json`**: Google OAuth2 token (auto-generated)

### Documentation
- **`README.md`**: Main project documentation
- **`GOOGLE_SHEETS_SETUP.md`**: Google Sheets API setup guide
- **`GOOGLE_SHEETS_INFO.md`**: Google Sheets quick reference
- **`N8N_WORKFLOW_SHARING.md`**: n8n workflow setup guide
- **`PROJECT_SUMMARY.md`**: This file

### Automation Files
- **`Gumtree Scraper Automation - n8n.cloud with Duplicate Detection.json`**: n8n workflow definition (current version)
- **`n8n_execute_scraper.sh`**: Shell script for local n8n execution

### Output
- **`output/`**: Directory containing scraped data
  - `gumtree_data.json`: JSON output (for n8n)
  - `gumtree_data.csv`: CSV output
  - `gumtree_data_*.xlsx`: Excel output with timestamps

## Key Features

### Data Extraction
- Job ID, title, URL, location, category
- Creation date and last edited date (converted from relative dates)
- Full description text
- Phone number detection (from description or "Show number" check)
- Phone reveal URL (when phone number exists)

### Data Storage
- **Primary**: Google Sheets (with duplicate detection)
- **Secondary**: Local JSON/CSV/Excel files

### Automation
- **Railway Deployment**: Flask API server deployed on Railway for cloud execution
- **n8n.cloud Integration**: HTTP API endpoints for workflow automation
- **Local Execution**: Direct Python script execution
- **Automatic Duplicate Detection**: Prevents duplicate entries in Google Sheets

## Current Configuration

### Main Settings (`main.py`)
```python
CATEGORY_URL = os.environ.get("CATEGORY_URL", "s-farming-veterinary/nsw/c21210l3008839")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "1"))
MAX_LISTINGS = 2  # Hardcoded (can be overridden via API)
LOCATION = os.environ.get("LOCATION", "")
EXPORT_FORMAT = os.environ.get("EXPORT_FORMAT", "all")
```

**Note**: Configuration uses environment variables (for Railway) with fallback defaults (for local development).

### Google Sheets
- Sheet ID: `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA`
- Email: `robi99ssr@gmail.com`
- Range: `Sheet1!A:Z`

### Scrapfly
- Country: `AU` (Australia)
- Base URL: `https://www.gumtree.com.au`
- API Key: Configured in `config.py`

## Extracted Fields

1. `job_id` - Unique listing identifier
2. `title` - Listing title
3. `url` - Full URL to listing
4. `location` - Location of listing
5. `categoryName` - Category name
6. `creationDate` - Date listed (YYYY-MM-DD)
7. `description` - Full description text
8. `phone` - Phone number (if found)
9. `phoneNumberExists` - Boolean for phone availability
10. `phoneRevealUrl` - API URL to reveal phone (if phone exists)
11. `lastEdited` - Last edited date (YYYY-MM-DD)
12. `scraped_at` - Scraping timestamp
13. `success` - Scraping success status

## Quick Start

### Local Execution
1. Install dependencies: `pip install -r requirements.txt`
2. Set up Google Sheets (see `GOOGLE_SHEETS_SETUP.md`)
3. Configure settings via environment variables or edit `main.py`
4. Run: `python3 main.py`

### Railway Deployment
1. Deploy to Railway (uses `Procfile` for gunicorn server)
2. Set environment variables in Railway dashboard
3. Access API at: `https://your-railway-app.up.railway.app/scrape`

### n8n.cloud Integration
1. Import workflow: `Gumtree Scraper Automation - n8n.cloud with Duplicate Detection.json`
2. Configure Railway API URL in workflow
3. Set up schedule or manual trigger

## Verification Checklist

✅ All Python files compile successfully
✅ All imports work correctly
✅ Google Sheets column order includes all fields
✅ Phone number detection logic implemented
✅ Date extraction from API implemented
✅ Duplicate detection working
✅ Output file clearing implemented
✅ n8n workflow configured
✅ Documentation updated

## Notes

- **Configuration**: Uses environment variables for Railway deployment, with fallback defaults for local development
- **API Server**: Flask API server (`api_server.py`) handles HTTP requests from n8n.cloud
- **Local Execution**: `main.py` can be run directly for local testing
- **Output Files**: Local output files are overwritten on each run
- **Google Sheets**: Only appends new records (duplicates detected by `job_id` and `url`)
- **Phone Numbers**: Extracted from descriptions or detected via "Show number" button
- **Dates**: Converted from relative format ("2 days ago") to exact dates (YYYY-MM-DD)
- **Column Order**: All data is saved in consistent column order across all export formats

