# Google Sheets Configuration Info

## Quick Reference

- **Google Sheet ID**: `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA`
- **Google Sheet URL**: https://docs.google.com/spreadsheets/d/1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA/edit
- **Credentials File**: `/Users/sakib/Salaheddine Mokhtari/credentials.json` ✅ (exists)
- **Token File**: `token.json` (will be created on first run)
- **Email for Sheet Sharing**: `robi99ssr@gmail.com`

## Important Notes

1. **Share the Google Sheet** with `robi99ssr@gmail.com` and give it **Editor** permissions
2. On first run, the scraper will open a browser for authentication
3. After authentication, `token.json` will be created automatically
4. The scraper will only append **new records** (duplicates based on `job_id` or `url` are skipped)

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

