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
3. Sign in with the Google account that has access to the sheet
4. Click **Allow** to grant permissions
5. A `token.json` file will be created automatically (this stores your access token)

## Step 6: Verify Setup

1. Run the scraper again
2. Check your Google Sheet - new data should appear
3. The scraper will only append new records (duplicates based on `job_id` or `url` are skipped)

## Troubleshooting

### "credentials.json not found"
- Make sure `credentials.json` is in the project root directory
- Check the file name is exactly `credentials.json` (case-sensitive)

### "Access denied" or "Permission denied"
- Make sure you've shared the Google Sheet with the email associated with your Google Cloud project
- Verify the email has Editor permissions

### "Token expired"
- Delete `token.json` and run the scraper again to re-authenticate

### "Module not found" errors
- Install required packages: `pip install -r requirements.txt`

## Notes

- The `token.json` file contains your access token - keep it secure
- The scraper automatically detects duplicates using `job_id` and `url` fields
- Only new records are appended to the sheet
- If Google Sheets save fails, the scraper will fall back to saving local JSON/CSV files

