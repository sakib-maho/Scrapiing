# Google Sheets API Setup Guide

This guide will help you set up Google Sheets API credentials to enable saving scraped data directly to Google Sheets.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project name

## Step 2: Enable Google Sheets API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google Sheets API"
3. Click on it and click **Enable**

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - Choose **External** (unless you have a Google Workspace account)
   - Fill in the required fields (App name, User support email, Developer contact)
   - Add your email to test users
   - Click **Save and Continue** through the scopes (defaults are fine)
   - Click **Save and Continue** for test users
   - Click **Back to Dashboard**
4. Back in Credentials:
   - Application type: **Desktop app**
   - Name: "Gumtree Scraper" (or any name you prefer)
   - Click **Create**
5. Click **Download JSON** to download the credentials file
6. Rename the downloaded file to `credentials.json`
7. Move `credentials.json` to the project root directory (same folder as `main.py`)

## Step 4: Share Google Sheet

1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA/edit
2. Click **Share** button (top right)
3. Add the email address: **robi99ssr@gmail.com** (or the email associated with your Google Cloud project)
4. Give it **Editor** permissions
5. Click **Send**

## Step 5: First Run Authentication

1. Run the scraper: `python3 main.py`
2. On first run, a browser window will open asking you to authorize the application
3. Sign in with the Google account that has access to the sheet (`robi99ssr@gmail.com`)
4. Click **Allow** to grant permissions
5. A `token.json` file will be created automatically in the project root (this stores your access token)
6. The browser window will close automatically after successful authentication

## Step 6: Verify Setup

1. Run the scraper again: `python3 main.py`
2. Check your Google Sheet - new data should appear
3. The scraper will:
   - Print how many new records were appended
   - Print the Google Sheet URL
   - Save local JSON/CSV/Excel files as backup
4. The scraper will only append new records (duplicates based on `job_id` or `url` are skipped)
5. On first run, column headers will be automatically created

## Troubleshooting

### "credentials.json not found" or "Google credentials file not found"
- Make sure `credentials.json` is in the project root directory (same folder as `main.py`)
- Check the file name is exactly `credentials.json` (case-sensitive)
- Verify the file was downloaded from Google Cloud Console and not renamed incorrectly

### "Access denied" or "Permission denied" or "Error 403: access_denied"
- Make sure you've shared the Google Sheet with the email associated with your Google Cloud project (`robi99ssr@gmail.com`)
- Verify the email has **Editor** permissions (not just Viewer)
- If the app is in testing mode, make sure your email is added as a test user in Google Cloud Console:
  - Go to **APIs & Services** > **OAuth consent screen**
  - Scroll to **Test users** section
  - Click **Add Users** and add `robi99ssr@gmail.com`
- Delete `token.json` and re-authenticate

### "Token expired" or "Invalid credentials"
- Delete `token.json` from the project root directory
- Run the scraper again to re-authenticate
- A new browser window will open for authentication

### "Module not found" errors
- Install required packages: `pip install -r requirements.txt`
- Make sure you're in the virtual environment: `source venv/bin/activate`

### "Google Sheets ID not configured"
- Check `config.py` - `GOOGLE_SHEETS_ID` should be set to `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA`

### Google Sheets save fails but local files are saved
- This is expected behavior - the scraper always saves local files as backup
- Check the error message in the console for specific Google Sheets API errors
- Verify your Google Cloud project has Google Sheets API enabled
- Check your Scrapfly API quota (if applicable)

## Notes

- **Security**: Both `credentials.json` and `token.json` contain sensitive information
  - These files are automatically ignored by git (via `.gitignore`)
  - **Never commit these files to version control**
  - Keep them secure and don't share them publicly
- **Duplicate Detection**: The scraper automatically detects duplicates using `job_id` and `url` fields
- **Data Appending**: Only new records are appended to the sheet (existing records are skipped)
- **Backup Files**: Local JSON/CSV/Excel files are **always saved** as backup, even when Google Sheets save succeeds
- **Column Order**: 13 columns are saved in a specific order (see `GOOGLE_SHEETS_INFO.md` for details)
- **First Run**: On the first run, column headers are automatically created in the Google Sheet
- **Error Handling**: If Google Sheets save fails, the scraper will:
  - Print a warning message
  - Continue to save local files
  - Return success status for the scraping operation (only Google Sheets save fails)

