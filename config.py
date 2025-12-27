"""
Configuration file for Gumtree Scraping Automation
"""
import os
from typing import Dict

# Scrapfly API Configuration
SCRAPFLY_API_KEY = "Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd"
SCRAPFLY_API_URL = "https://api.scrapfly.io/scrape"

# Gumtree Credentials
GUMTREE_EMAIL = "pepeandamino@gmail.com"
GUMTREE_PASSWORD = "-trust555-"

# Scrapfly API Settings
SCRAPFLY_CONFIG = {
    "api_key": SCRAPFLY_API_KEY,
    "url": SCRAPFLY_API_URL,
    "render_js": True,  # Enable JavaScript rendering
    "country": "AU",  # Australia for Gumtree
    "premium_proxy": True,  # Use premium proxies
    "asp": True,  # Anti-scraping protection
}

# Gumtree Base URLs (Australian site only)
GUMTREE_BASE_URL = "https://www.gumtree.com.au"  # Australian site
GUMTREE_LOGIN_URL = f"{GUMTREE_BASE_URL}/login.html"

# Output Configuration
OUTPUT_DIR = "output"
DATA_FILE = f"{OUTPUT_DIR}/gumtree_data.json"
CSV_FILE = f"{OUTPUT_DIR}/gumtree_data.csv"

# Google Sheets Configuration
GOOGLE_SHEETS_ID = "1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA"
GOOGLE_SHEETS_RANGE = "Sheet1!A:Z"  # Adjust range as needed
GOOGLE_CREDENTIALS_FILE = "credentials.json"  # Path to OAuth2 credentials file
GOOGLE_TOKEN_FILE = "token.json"  # Path to store access token

# Scraping Settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds
DELAY_BETWEEN_REQUESTS = 1  # seconds

# Headers for requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def get_config() -> Dict:
    """Get complete configuration dictionary"""
    return {
        "scrapfly": SCRAPFLY_CONFIG,
        "gumtree": {
            "email": GUMTREE_EMAIL,
            "password": GUMTREE_PASSWORD,
            "base_url": GUMTREE_BASE_URL,
            "login_url": GUMTREE_LOGIN_URL,
        },
        "output": {
            "dir": OUTPUT_DIR,
            "data_file": DATA_FILE,
            "csv_file": CSV_FILE,
        },
        "google_sheets": {
            "sheet_id": GOOGLE_SHEETS_ID,
            "range": GOOGLE_SHEETS_RANGE,
            "credentials_file": GOOGLE_CREDENTIALS_FILE,
            "token_file": GOOGLE_TOKEN_FILE,
        },
        "scraping": {
            "max_retries": MAX_RETRIES,
            "retry_delay": RETRY_DELAY,
            "timeout": REQUEST_TIMEOUT,
            "delay": DELAY_BETWEEN_REQUESTS,
        },
        "headers": DEFAULT_HEADERS,
    }
