# Gumtree Scraping Automation

A comprehensive web scraping automation tool for Gumtree Australia using Scrapfly API. This tool scrapes category listings, extracts detailed information, and automatically saves data to Google Sheets with duplicate detection.

## Features

- **Scrapfly API Integration**: Uses Scrapfly's anti-scraping protection and premium proxies
- **Australian Gumtree Only**: Configured specifically for `gumtree.com.au`
- **Category Scraping**: Scrape entire categories with pagination support
- **Detailed Listing Extraction**: Get comprehensive information from individual listings
- **Phone Number Detection**: Automatically detects phone numbers in descriptions and checks for "Show number" availability
- **Date Extraction**: Extracts creation date and last edited date (converts relative dates to exact dates)
- **Google Sheets Integration**: Automatically saves data to Google Sheets with duplicate detection
- **Multiple Export Formats**: Export data as JSON, CSV, or Excel
- **n8n Workflow Support**: Includes ready-to-use n8n workflow for automation
- **Data Statistics**: Get insights about scraped data
- **Error Handling**: Robust error handling and retry mechanisms


## Prerequisites

- Python 3.8 or higher (tested with Python 3.14)
- Scrapfly API key (already configured)
- Google Sheets API credentials (see [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md))
- n8n (optional, for workflow automation)

## Installation

1. Clone or download this repository

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Sheets API (see [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md))

## Configuration

### Main Configuration (`main.py`)

The scraper uses hardcoded configuration in `main.py`:

```python
CATEGORY_URL = "s-farming-veterinary/nsw/c21210l3008839"
MAX_PAGES = 1
MAX_LISTINGS = 5  # Maximum number of listings to scrape (None = scrape all)
LOCATION = ""  # Optional location filter
EXPORT_FORMAT = "all"  # Options: "json", "csv", "excel", "all"
```

Modify these values directly in `main.py` to change scraping behavior.

### API Configuration (`config.py`)

- **Scrapfly API Key**: Already configured
- **Google Sheets ID**: Already configured
- **Country**: Set to `AU` (Australia)
- **Base URL**: `https://www.gumtree.com.au`

## Usage

### Basic Usage

Simply run:
```bash
python3 main.py
```

The scraper will:
1. Scrape the configured category
2. Extract detailed information from each listing
3. Save data to Google Sheets (appends only new records)
4. Save JSON locally for n8n workflow compatibility
5. Display statistics

### Output

Data is saved in two locations:

1. **Google Sheets**: Primary storage with automatic duplicate detection
   - Sheet ID: `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA`
   - Only new records are appended (duplicates based on `job_id` or `url` are skipped)

2. **Local Files** (`output/` directory):
   - `gumtree_data.json` - JSON format with metadata (for n8n workflow)
   - `gumtree_data.csv` - CSV format
   - `gumtree_data_[timestamp].xlsx` - Excel format

**Note**: Local files are overwritten on each run (old files are cleared before saving new data).

## Extracted Data Fields

Each listing contains the following fields:

- `job_id`: Unique listing identifier
- `title`: Listing title
- `url`: Full URL to the listing
- `location`: Location of the listing
- `categoryName`: Category name
- `creationDate`: Date when listing was created (YYYY-MM-DD format)
- `description`: Full description text
- `phone`: Phone number (if found in description, otherwise `null`)
- `phoneNumberExists`: Boolean indicating if "Show number" is available
- `phoneRevealUrl`: Direct API URL to reveal phone number (only when `phoneNumberExists` is `true`)
- `lastEdited`: Date when listing was last edited (YYYY-MM-DD format)
- `scraped_at`: Timestamp of when the data was scraped
- `success`: Boolean indicating if scraping was successful

### Date Conversion

The scraper automatically converts relative dates to exact dates:
- "Today" → Current date
- "Yesterday" → Previous date
- "X hours ago" → Calculated date
- "X days ago" → Calculated date
- "X weeks ago" → Calculated date
- "X months ago" → Calculated date (approximate)
- "DD/MM/YYYY" → Standardized format
- "DD Mon YYYY" → Standardized format

### Phone Number Detection

The scraper uses a two-step process:

1. **Description Check**: First checks if a phone number exists in the listing description snippet (from search results page)
   - If found: Extracts phone number, sets `phoneNumberExists = true`, skips visiting the listing page
   - Supports Australian phone formats: `04XX XXX XXX`, `+61 4XX XXX XXX`, `0X XXXX XXXX`, etc.

2. **Listing Page Check**: If no phone found in description, visits the listing page to check for "Show number" text
   - If "Show number" exists: Sets `phoneNumberExists = true` and provides `phoneRevealUrl`
   - If not found: Sets `phoneNumberExists = false`

## n8n Workflow Automation

The project includes a ready-to-use n8n workflow for automated scraping.

### Setup

1. Install n8n: `npm install -g n8n` or use `npx n8n`
2. Import workflow: `Gumtree Scraper Automation.json`
3. Configure paths in the workflow nodes
4. Run manually or set up a schedule trigger

See [N8N_WORKFLOW_SHARING.md](N8N_WORKFLOW_SHARING.md) for detailed setup instructions.

## Project Structure

```
.
├── config.py                      # Configuration settings
├── scrapfly_client.py             # Scrapfly API client
├── gumtree_scraper.py             # Main scraper class
├── data_handler.py                # Data export and Google Sheets integration
├── main.py                        # Main execution script
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── GOOGLE_SHEETS_SETUP.md         # Google Sheets API setup guide
├── GOOGLE_SHEETS_INFO.md          # Google Sheets quick reference
├── N8N_WORKFLOW_SHARING.md        # n8n workflow setup guide
├── Gumtree Scraper Automation.json # n8n workflow definition
├── n8n_execute_scraper.sh         # Shell script for n8n execution
├── credentials.json                # Google OAuth2 credentials (not in repo)
├── token.json                      # Google OAuth2 token (auto-generated)
└── output/                         # Output directory (created automatically)
    ├── gumtree_data.json
    ├── gumtree_data.csv
    └── gumtree_data_*.xlsx
```

## Scrapfly API Features

This tool leverages Scrapfly's advanced features:
- **JavaScript Rendering**: Handles dynamic content
- **Premium Proxies**: High-quality residential proxies
- **Anti-Scraping Protection**: Bypasses common anti-bot measures
- **Country Targeting**: Configured for Australia (AU)
- **Rate Limit Handling**: Automatically respects `Retry-After` headers

## Google Sheets Integration

The scraper automatically saves data to Google Sheets with the following features:

- **Duplicate Detection**: Compares `job_id` and `url` to skip existing records
- **Automatic Headers**: Creates column headers on first run
- **Consistent Column Order**: Maintains the same column order as JSON output
- **Error Handling**: Falls back to local files if Google Sheets save fails

See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for setup instructions.

## Error Handling

The scraper includes:
- Automatic retries for failed requests
- Rate limiting to avoid being blocked
- Comprehensive error logging
- Graceful handling of missing data
- Timeout detection and fallback mechanisms
- Concurrent access error prevention

## Limitations

1. **Australian Site Only**: Configured specifically for `gumtree.com.au`
2. **Dynamic Content**: Some content may require JavaScript rendering (handled by Scrapfly)
3. **Rate Limits**: Be mindful of Scrapfly API rate limits and Gumtree's terms of service
4. **Phone Number Extraction**: Phone numbers are only extracted if present in descriptions or if "Show number" is available (requires login for API call)

## Best Practices

1. **Respect Rate Limits**: The scraper includes delays between requests
2. **Use Appropriate Limits**: Set `MAX_LISTINGS` to avoid excessive scraping
3. **Check Terms of Service**: Ensure your usage complies with Gumtree's ToS
4. **Monitor API Usage**: Keep track of your Scrapfly API usage
5. **Regular Backups**: Google Sheets data is automatically saved, but consider regular exports

## Troubleshooting

### No listings found
- Check if the category URL in `main.py` is correct
- Verify that listings exist for your category
- Check network connectivity and API key validity

### Google Sheets save fails
- Verify `credentials.json` exists and is valid
- Check that the Google Sheet is shared with the correct email
- Ensure `token.json` is not expired (delete it to re-authenticate)
- See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed troubleshooting

### API errors
- Verify Scrapfly API key is valid
- Check your Scrapfly account balance
- Review Scrapfly API documentation for any changes
- Check for rate limiting (the scraper will automatically retry with delays)

### Phone numbers not extracted
- Phone numbers are only extracted if they appear in the description or if "Show number" is available
- The scraper uses Australian phone number patterns - other formats may not be detected
- Check the description field in the output to see if phone numbers are present

### Dates are null
- The scraper uses multiple methods to extract dates (API, JavaScript data, HTML)
- If dates are still null, check the debug HTML files (if enabled)
- Some listings may not have date information available

## Support

For issues or questions:
1. Check the error messages in the console
2. Review the setup guides:
   - [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md)
   - [N8N_WORKFLOW_SHARING.md](N8N_WORKFLOW_SHARING.md)
3. Verify configuration settings in `config.py` and `main.py`
4. Check Scrapfly API documentation

## License

This project is provided as-is for educational and research purposes. Ensure compliance with Gumtree's Terms of Service and applicable laws when using this tool.
