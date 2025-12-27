# Google Sheets Configuration Info

## Quick Reference

- **Google Sheet ID**: `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA`
- **Google Sheet URL**: https://docs.google.com/spreadsheets/d/1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA/edit
- **Credentials File**: `credentials.json` (must be in project root directory)
- **Token File**: `token.json` (auto-created on first run)
- **Email for Sheet Sharing**: `robi99ssr@gmail.com`
- **Sheet Range**: `Sheet1!A:Z`

## Important Notes

1. **Share the Google Sheet** with `robi99ssr@gmail.com` and give it **Editor** permissions
2. On first run, the scraper will open a browser for authentication
3. After authentication, `token.json` will be created automatically
4. The scraper will only append **new records** (duplicates based on `job_id` or `url` are skipped)
5. **Local files are always saved** as backup (JSON, CSV, Excel) even if Google Sheets save succeeds
6. If Google Sheets save fails, the scraper will still save to local files

## Columns Saved to Google Sheets

The following 13 columns are saved in this order:
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
11. `scraped_at` - Scraping timestamp
12. `lastEdited` - Last edited date (YYYY-MM-DD)
13. `success` - Scraping success status

## Testing

Run the scraper:
```bash
python3 main.py
```

The scraper will:
1. Scrape listings from Gumtree
2. Check existing data in Google Sheets
3. Append only new records (skip duplicates)
4. Print how many new records were added
5. Print the Google Sheet URL after successful save
6. Always save JSON locally for n8n workflow compatibility

