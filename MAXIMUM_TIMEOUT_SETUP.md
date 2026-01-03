# Maximum Timeout Setup for Railway and n8n

This guide shows how to set maximum timeout limits so scraping doesn't timeout before finishing.

## Current Timeouts

| Service | Current | Location |
|---------|---------|----------|
| **Railway (Gunicorn)** | 1200 seconds (20 min) | `Procfile`, `railway.json` |
| **n8n HTTP Request** | 1500000ms (25 min) | n8n workflow settings |
| **Railway Platform** | Varies by plan | Railway dashboard settings |

## Timeout Calculation

### Scraping Time Estimate:
- **1 listing detail fetch:** ~3-5 seconds
- **24 listings (1 page):** ~2-4 minutes
- **48 listings (2 pages):** ~4-8 minutes
- **72 listings (3 pages):** ~6-12 minutes
- **96 listings (4 pages):** ~8-16 minutes
- **120 listings (5 pages):** ~10-20 minutes

**Add 50% buffer for safety:**
- 2 pages: 8 min × 1.5 = **12 minutes minimum**
- 3 pages: 12 min × 1.5 = **18 minutes minimum**
- 5 pages: 20 min × 1.5 = **30 minutes minimum**

## Step 1: Increase Railway Timeout (Gunicorn)

### Option A: Update Procfile (Recommended)

Edit `Procfile`:
```bash
web: gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 3600 --keep-alive 120 api_server:app
```

**Timeout values:**
- `1200` = 20 minutes (current)
- `1800` = 30 minutes (for 2-3 pages)
- `3600` = 60 minutes (for 5+ pages, maximum recommended)
- `7200` = 120 minutes (2 hours, very long scrapes)

### Option B: Update railway.json

Edit `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 3600 --keep-alive 120 api_server:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Option C: Railway Dashboard Settings

1. Go to **Railway Dashboard** → Your Service
2. Click **Settings** tab
3. Look for **"Timeout"** or **"Request Timeout"** setting
4. If available, set to:
   - **1800 seconds** (30 minutes) for 2-3 pages
   - **3600 seconds** (60 minutes) for 5+ pages
5. **Save** and **Redeploy**

**Note:** Railway platform timeout may override Gunicorn timeout. Check Railway dashboard for platform-level limits.

## Step 2: Increase n8n Timeout

### In n8n.cloud Workflow

1. **Open your workflow** in n8n.cloud
2. **Click on "Call Scraper API"** node (or HTTP Request node)
3. **Click "Options"** (at the bottom of node settings)
4. **Find "Timeout" field**
5. **Set timeout value** (in milliseconds):

| Scraping Scope | Timeout (ms) | Timeout (minutes) |
|----------------|--------------|-------------------|
| 1 page (24 listings) | `900000` | 15 minutes |
| 2 pages (48 listings) | `1800000` | 30 minutes |
| 3 pages (72 listings) | `2700000` | 45 minutes |
| 5 pages (120 listings) | `3600000` | 60 minutes |
| Maximum (safe) | `5400000` | 90 minutes |

6. **Click "Save"**
7. **Save the workflow**

### Timeout Formula

```
Timeout (ms) = (pages × 24 listings × 4 seconds × 1.5 buffer) × 1000
```

**Examples:**
- 2 pages: `(2 × 24 × 4 × 1.5) × 1000 = 288000ms` → Use `1800000ms` (30 min)
- 5 pages: `(5 × 24 × 4 × 1.5) × 1000 = 720000ms` → Use `3600000ms` (60 min)

## Step 3: Recommended Timeout Values

### For 2 Pages (48 listings):

**Railway (Gunicorn):**
```bash
--timeout 1800
```
(30 minutes)

**n8n:**
```
1800000
```
(30 minutes in milliseconds)

### For 5 Pages (120 listings):

**Railway (Gunicorn):**
```bash
--timeout 3600
```
(60 minutes)

**n8n:**
```
3600000
```
(60 minutes in milliseconds)

### Maximum Safe Values:

**Railway (Gunicorn):**
```bash
--timeout 3600
```
(60 minutes - maximum recommended)

**n8n:**
```
5400000
```
(90 minutes - very safe buffer)

## Step 4: Update Files

### Update Procfile

```bash
web: gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 3600 --keep-alive 120 api_server:app
```

### Update railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 3600 --keep-alive 120 api_server:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Step 5: Deploy and Test

1. **Commit and push** the updated files
2. **Railway will auto-deploy** (if connected to GitHub)
3. **Or manually redeploy** in Railway dashboard
4. **Update n8n timeout** in workflow settings
5. **Test with 2 pages:**
   ```json
   {
     "max_pages": 2
   }
   ```

## Important Notes

### Railway Platform Limits

Railway may have platform-level timeouts that override Gunicorn:
- **Free tier:** Usually 20-30 minutes
- **Pro tier:** Usually 60+ minutes
- **Check Railway dashboard** for your plan's limits

### n8n Limits

- **n8n.cloud free tier:** May have timeout limits
- **n8n.cloud paid tier:** Usually higher limits
- **Self-hosted n8n:** No limits (set as needed)

### Best Practices

1. **Set n8n timeout > Railway timeout:**
   - Railway: 30 minutes
   - n8n: 35-40 minutes (buffer)

2. **Monitor actual scraping time:**
   - Check Railway logs
   - Adjust timeouts based on real performance

3. **Start conservative, increase as needed:**
   - Start with 30 minutes
   - Increase if scraping takes longer

## Troubleshooting

### Still Timing Out?

1. **Check Railway logs:**
   - See if scraping actually completes
   - Check for error messages

2. **Check n8n timeout:**
   - Make sure it's set correctly
   - Should be higher than Railway timeout

3. **Check Railway platform limits:**
   - Dashboard → Settings → Timeout
   - May need to upgrade plan

4. **Reduce scraping scope:**
   - Try 1 page first
   - Gradually increase

### Railway Container Restarts

If Railway container restarts:
- **Check Railway logs** for memory/CPU issues
- **Check Scrapfly quota** (may be exhausted)
- **Reduce scraping scope** temporarily

## Quick Reference

### For 2 Pages Scraping:

**Railway:**
```bash
--timeout 1800
```

**n8n:**
```
1800000
```

### For 5 Pages Scraping:

**Railway:**
```bash
--timeout 3600
```

**n8n:**
```
3600000
```

### Maximum Safe (Any Scope):

**Railway:**
```bash
--timeout 3600
```

**n8n:**
```
5400000
```

## Summary

✅ **Railway timeout:** Set in `Procfile` and `railway.json` (Gunicorn `--timeout`)
✅ **n8n timeout:** Set in workflow node options (milliseconds)
✅ **Rule:** n8n timeout should be > Railway timeout
✅ **Recommended:** 30 minutes for 2 pages, 60 minutes for 5 pages
✅ **Maximum:** 60 minutes Railway, 90 minutes n8n (safe buffer)

After updating, your scraping should complete without timeouts! 🎉

