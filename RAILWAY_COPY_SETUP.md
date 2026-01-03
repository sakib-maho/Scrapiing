# Setting Up a Copy of the Project in Railway for n8n

When creating a **new copy** of this project in Railway, here's everything you need to change to make it work with n8n.

## 📋 Quick Checklist

- [ ] Deploy new project to Railway
- [ ] Get new Railway URL
- [ ] Set environment variables in new Railway project
- [ ] Upload Google credentials (if using Google Sheets)
- [ ] Update n8n workflow with new URL
- [ ] Test the connection

---

## Step 1: Deploy to Railway (New Project)

1. Go to **https://railway.app**
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository (same or forked copy)
4. Railway will auto-detect Python and deploy
5. Wait for deployment to complete (2-3 minutes)

## Step 2: Get Your New Railway URL

1. Click on your **new project** in Railway
2. Click on the **service**
3. Go to **"Settings"** → **"Domains"**
4. Click **"Generate Domain"**
5. Copy the URL: `https://your-new-app.up.railway.app`
6. **Save this URL!** You'll need it for n8n

## Step 3: Set Environment Variables in New Railway Project

Go to your **new Railway project** → **Service** → **"Variables"** tab

### Required Environment Variables

Click **"New Variable"** and add these:

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `SCRAPFLY_API_KEY` | `Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd` | Your Scrapfly API key |
| `GUMTREE_EMAIL` | `pepeandamino@gmail.com` | Gumtree account email |
| `GUMTREE_PASSWORD` | `-trust555-` | Gumtree account password |
| `GOOGLE_SHEETS_ID` | `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA` | Your Google Sheet ID |

### Optional Environment Variables (for defaults)

| Variable Name | Default Value | Description |
|--------------|---------------|-------------|
| `CATEGORY_URL` | `s-farming-veterinary/nsw/c21210l3008839` | Default category to scrape |
| `MAX_PAGES` | `1` | Default max pages |
| `MAX_LISTINGS` | `24` | Default max listings |
| `LOCATION` | `""` | Default location filter |

**Note:** These are optional - n8n can override them in the API request.

## Step 4: Upload Google Sheets Credentials (If Using Google Sheets)

If you want the scraper to save to Google Sheets, you need to upload credentials.

### Option A: Using Railway CLI (Recommended)

```bash
# Install Railway CLI (if not already installed)
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your new project (select it when prompted)
railway link

# Upload credentials.json
railway variables set GOOGLE_CREDENTIALS="$(cat credentials.json)"

# Upload token.json
railway variables set GOOGLE_TOKEN="$(cat token.json)"
```

### Option B: Manual Upload via Railway Dashboard

1. Open `credentials.json` file
2. Copy the **entire JSON content**
3. In Railway: **Variables** → **New Variable**
   - Name: `GOOGLE_CREDENTIALS`
   - Value: Paste the entire JSON (no quotes needed)
4. Open `token.json` file
5. Copy the **entire JSON content**
6. In Railway: **Variables** → **New Variable**
   - Name: `GOOGLE_TOKEN`
   - Value: Paste the entire JSON (no quotes needed)

### Option C: Skip Google Sheets (If Not Needed)

If you don't need Google Sheets:
- Set `save_to_sheets: false` in n8n workflow
- The API will still return all data as JSON
- You can process the JSON in n8n instead

## Step 5: Redeploy After Adding Variables

After adding environment variables:

1. Go to **Deployments** tab in Railway
2. Click **"Redeploy"** (or wait for auto-redeploy)
3. Wait for deployment to complete

**Important:** Variables only take effect after redeployment!

## Step 6: Update n8n Workflow

### Update the API URL

1. Go to **https://sakib162.app.n8n.cloud/home/workflows** (or your n8n instance)
2. Open your workflow
3. Click on the **"Call Scraper API"** node (or HTTP Request node)
4. In the **"URL"** field, change it to your new Railway URL:
   ```
   https://your-new-app.up.railway.app/scrape
   ```
5. Verify settings:
   - **Method:** POST
   - **Content-Type:** application/json
   - **Body:** Should have your JSON parameters
6. Click **"Save"**

### Update Workflow Parameters (Optional)

In the **"Call Scraper API"** node, you can set these parameters:

```json
{
  "category_url": "s-hospitality-tourism/sydney/c18342l3003435",
  "max_pages": 1,
  "max_listings": 24,
  "location": "",
  "save_to_sheets": true
}
```

**Note:** These parameters override Railway environment variables.

## Step 7: Test the Connection

### Test 1: Health Check

```bash
curl https://your-new-app.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "service": "Gumtree Scraper API"}
```

### Test 2: Test Scrape Endpoint

```bash
curl -X POST https://your-new-app.up.railway.app/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "max_pages": 1,
    "max_listings": 2,
    "save_to_sheets": false
  }'
```

### Test 3: Test from n8n

1. In n8n, click **"Execute Workflow"**
2. Wait for execution to complete
3. Check the results:
   - Should show `"success": true`
   - Should show listings found
   - Should show `"google_sheets_saved": true` (if credentials are set)

## Step 8: Verify Everything Works

✅ **Checklist:**

- [ ] Railway deployment is successful
- [ ] Health endpoint responds: `https://your-new-app.up.railway.app/health`
- [ ] All environment variables are set in Railway
- [ ] Google credentials uploaded (if using Google Sheets)
- [ ] n8n workflow updated with new URL
- [ ] Test execution in n8n succeeds
- [ ] Data appears in Google Sheets (if enabled)

## 🔄 What's Different from the Original?

When you create a **copy** of the project, these are the **only things** that need to change:

1. **Railway URL** - Each new deployment gets a unique URL
2. **Environment Variables** - Need to be set in the new Railway project
3. **Google Credentials** - Need to be uploaded to the new Railway project
4. **n8n Workflow URL** - Needs to point to the new Railway URL

**Everything else stays the same:**
- ✅ Code files (no changes needed)
- ✅ `requirements.txt` (no changes needed)
- ✅ `Procfile` (no changes needed)
- ✅ `config.py` (no changes needed - uses environment variables)
- ✅ API endpoints (same: `/health` and `/scrape`)

## 🆘 Troubleshooting

### "Connection refused" or "ENOTFOUND"
- ✅ Check the URL is correct in n8n workflow
- ✅ Make sure Railway service is running (check Railway dashboard)
- ✅ Test health endpoint: `curl https://your-new-app.up.railway.app/health`

### "Timeout" errors
- ✅ Scraping can take 10-20 minutes for many listings
- ✅ In n8n: Set timeout to `1800000` (30 minutes) in HTTP Request node
- ✅ See `N8N_TIMEOUT_FIX.md` for detailed timeout configuration

### Google Sheets not saving
- ✅ Check Railway logs for authentication errors
- ✅ Verify `GOOGLE_CREDENTIALS` and `GOOGLE_TOKEN` are set in Railway
- ✅ Make sure you **redeployed** after adding variables
- ✅ Check response shows `"google_sheets_saved": false` and look for warnings

### "FileNotFoundError: credentials.json"
- ✅ Make sure you uploaded `GOOGLE_CREDENTIALS` and `GOOGLE_TOKEN` as environment variables
- ✅ Redeploy after adding variables
- ✅ Check Railway logs for exact error

### No listings found
- ✅ Check if the category has listings on Gumtree
- ✅ Try a different category URL
- ✅ Check Railway logs for scraping errors
- ✅ Verify Scrapfly API key is correct

## 📝 Summary

**For a new Railway copy, you need to:**

1. ✅ Deploy to Railway (new project)
2. ✅ Get new Railway URL
3. ✅ Set environment variables (SCRAPFLY_API_KEY, GUMTREE_EMAIL, etc.)
4. ✅ Upload Google credentials (if using Google Sheets)
5. ✅ Update n8n workflow URL
6. ✅ Test and verify

**That's it!** The code itself doesn't need any changes - it's all configuration.

