# Project Summary

## Overview
Gumtree Scraping Automation for Australian listings with Google Sheets integration and n8n workflow support.

## Core Files

### Python Scripts
- **`main.py`**: Main execution script with hardcoded configuration
- **`gumtree_scraper.py`**: Main scraper class with all extraction logic
- **`scrapfly_client.py`**: Scrapfly API client wrapper
- **`data_handler.py`**: Data export and Google Sheets integration
- **`config.py`**: Configuration settings (API keys, URLs, etc.)

### Configuration Files
- **`requirements.txt`**: Python dependencies
- **`credentials.json`**: Google OAuth2 credentials (not in repo, user must add)
- **`token.json`**: Google OAuth2 token (auto-generated)

### Documentation
- **`README.md`**: Main project documentation
- **`GOOGLE_SHEETS_SETUP.md`**: Google Sheets API setup guide
- **`GOOGLE_SHEETS_INFO.md`**: Google Sheets quick reference
- **`N8N_WORKFLOW_SHARING.md`**: n8n workflow setup guide
- **`PROJECT_SUMMARY.md`**: This file

### Automation Files
- **`Gumtree Scraper Automation.json`**: n8n workflow definition
- **`n8n_execute_scraper.sh`**: Shell script for n8n execution

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
- n8n workflow support
- Manual trigger execution
- Automatic duplicate detection

## Current Configuration

### Main Settings (`main.py`)
```python
CATEGORY_URL = "s-farming-veterinary/nsw/c21210l3008839"
MAX_PAGES = 1
MAX_LISTINGS = 5
LOCATION = ""
EXPORT_FORMAT = "all"
```

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

1. Install dependencies: `pip install -r requirements.txt`
2. Set up Google Sheets (see `GOOGLE_SHEETS_SETUP.md`)
3. Configure settings in `main.py` if needed
4. Run: `python3 main.py`

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

- Local output files are overwritten on each run
- Google Sheets only appends new records (duplicates skipped)
- Phone numbers are extracted from descriptions or detected via "Show number"
- Dates are converted from relative format to exact dates
- All data is saved in consistent column order

