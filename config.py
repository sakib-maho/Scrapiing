"""
Configuration file for Gumtree Scraping Automation
"""
import os
from typing import Dict

# Scrapfly API Configuration
# Use environment variables for security, fallback to hardcoded for local development
SCRAPFLY_API_KEY = os.environ.get("SCRAPFLY_API_KEY", "scp-live-25a92d7242df4307a998a16ec72cf375")
SCRAPFLY_API_URL = os.environ.get("SCRAPFLY_API_URL", "https://api.scrapfly.io/scrape")

# Gumtree Credentials
# Use environment variables for security, fallback to hardcoded for local development
GUMTREE_EMAIL = os.environ.get("GUMTREE_EMAIL", "pepeandamino@gmail.com")
GUMTREE_PASSWORD = os.environ.get("GUMTREE_PASSWORD", "-trust555-")

# Scrapfly API Settings
SCRAPFLY_CONFIG = {
    "api_key": SCRAPFLY_API_KEY,
    "url": SCRAPFLY_API_URL,
    # Default to "fast" settings; scraper will automatically fallback to harder settings only when needed.
    "render_js": os.environ.get("SCRAPFLY_RENDER_JS_DEFAULT", "false").lower() == "true",
    "country": "AU",  # Australia for Gumtree
    "premium_proxy": os.environ.get("SCRAPFLY_PREMIUM_PROXY_DEFAULT", "false").lower() == "true",
    "asp": os.environ.get("SCRAPFLY_ASP_DEFAULT", "false").lower() == "true",
}

# Gumtree Base URLs (Australian site only)
GUMTREE_BASE_URL = "https://www.gumtree.com.au"  # Australian site
GUMTREE_LOGIN_URL = f"{GUMTREE_BASE_URL}/login.html"

# Output Configuration
OUTPUT_DIR = "output"
DATA_FILE = f"{OUTPUT_DIR}/gumtree_data.json"
CSV_FILE = f"{OUTPUT_DIR}/gumtree_data.csv"

# Google Sheets Configuration
GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID", "1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA")
GOOGLE_SHEETS_RANGE = os.environ.get("GOOGLE_SHEETS_RANGE", "Sheet1!A:Z")  # Adjust range as needed
GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")  # Path to OAuth2 credentials file
GOOGLE_TOKEN_FILE = os.environ.get("GOOGLE_TOKEN_FILE", "token.json")  # Path to store access token

# Scraping Settings
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.environ.get("RETRY_DELAY", "2"))  # seconds
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "240"))  # seconds
DELAY_BETWEEN_REQUESTS = float(os.environ.get("DELAY_BETWEEN_REQUESTS", "0.5"))  # seconds

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
