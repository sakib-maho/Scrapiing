# Railway Stuck Issue - Diagnosis and Fix

## Problem

When scraping 2 pages, Railway gets stuck at listing [20/24] on page 2 and the container stops/restarts.

## Root Causes

### 1. **Railway Timeout**
- Railway has a default timeout (usually 20-30 minutes for free tier)
- Scraping 2 pages × 24 listings = 48 requests
- Each request takes ~3-5 seconds = **15-30 minutes total**
- Railway may kill the container if it exceeds timeout

### 2. **Scrapfly Quota/Rate Limits**
- Scrapfly may run out of credits/quota during large scrapes
- 403 errors (quota exceeded) weren't being handled properly
- The scraper would hang or fail silently

### 3. **Missing Error Handling**
- Errors during listing detail fetches weren't logged clearly
- No graceful handling when Scrapfly fails

## Fixes Applied

### 1. Added Scrapfly 403 Error Handling
- Now detects when Scrapfly quota is exceeded (403)
- Stops scraping gracefully instead of hanging
- Logs clear error messages

### 2. Improved Error Logging
- Better error messages for rate limits (429)
- Clear messages for quota exceeded (403)
- Timeout errors are logged and handled
- Continues with basic listing data when detail fetch fails

### 3. Graceful Degradation
- If a listing detail fetch fails, continues with basic data
- Only stops completely if quota is exceeded (403)
- Rate limits (429) are logged but scraping continues

## How to Check Scrapfly Quota

### Option 1: Test Script
```bash
python3 test_scrapfly_quota.py
```

This will:
- Test Scrapfly API connection
- Check for rate limits (429)
- Check for quota exceeded (403)
- Show remaining credits if available

### Option 2: Check Scrapfly Dashboard
1. Go to https://scrapfly.io/dashboard
2. Check your account credits/quota
3. Look at usage statistics

## Solutions

### Solution 1: Check Scrapfly Quota First
```bash
# Run the test script
python3 test_scrapfly_quota.py
```

If quota is exhausted:
- Add more credits to your Scrapfly account
- Wait for quota to reset (if on a plan with monthly limits)

### Solution 2: Reduce Scraping Scope
If Scrapfly quota is fine but Railway times out:

**Option A: Reduce pages**
```json
{
  "max_pages": 1,
  "max_listings": 24
}
```

**Option B: Reduce listings per page**
```json
{
  "max_pages": 2,
  "max_listings": 30
}
```

### Solution 3: Increase Railway Timeout
1. Go to Railway Dashboard → Your Service → Settings
2. Look for "Timeout" or "Request Timeout"
3. Increase to at least 1800 seconds (30 minutes)
4. Redeploy

### Solution 4: Check Railway Logs
1. Railway Dashboard → Service → Deployments
2. View logs in real-time during scraping
3. Look for:
   - "Scrapfly quota exceeded (403)"
   - "Rate limit (429)"
   - Timeout errors
   - Container restart messages

## Expected Behavior After Fix

### If Scrapfly Quota Exceeded:
```
❌ [20/24] Scrapfly quota exceeded (403) - stopping scraping
Error: 403 Forbidden - Scrapfly quota/credits may be exhausted...
⚠️  Stopping scraping due to Scrapfly quota exceeded
✅ Scraping completed. Found 44 listings.
```

### If Rate Limited:
```
⚠️  [15/24] Rate limit (429) - continuing with basic data
[16/24] Fetching: ...
```

### If Request Fails/Timeout:
```
⚠️  [20/24] Request failed/timeout - continuing with basic data: ...
[21/24] Fetching: ...
```

## Testing

After deploying the fix:

1. **Test with 1 page first:**
```json
{
  "max_pages": 1,
  "max_listings": 5
}
```

2. **If successful, test with 2 pages:**
```json
{
  "max_pages": 2,
  "max_listings": 10
}
```

3. **Monitor Railway logs** during scraping to see:
   - Progress messages
   - Any error messages
   - When/why it stops

## Next Steps

1. ✅ **Deploy the fix** (push code to Railway)
2. ✅ **Check Scrapfly quota** using test script
3. ✅ **Test with smaller scope** first (1 page, 5 listings)
4. ✅ **Monitor Railway logs** during scraping
5. ✅ **Gradually increase** scope if successful

## Summary

The fix adds:
- ✅ Better error handling for Scrapfly quota (403)
- ✅ Better error handling for rate limits (429)
- ✅ Clear error logging
- ✅ Graceful degradation (continues with basic data when possible)
- ✅ Stops gracefully when quota is exceeded

The scraper will now:
- Log errors clearly
- Continue scraping when possible
- Stop gracefully when quota is exceeded
- Not hang indefinitely

