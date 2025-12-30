# Railway Quick Start Guide 🚀

Follow these steps to deploy your Gumtree Scraper API to Railway.

## Step 1: Push Code to GitHub

```bash
cd "/Users/sakib/Salaheddine Mokhtari"

# Check git status
git status

# If not initialized:
git init
git add .
git commit -m "Ready for Railway deployment"

# Create repo on GitHub.com, then:
git remote add origin https://github.com/YOUR_USERNAME/gumtree-scraper-api.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy to Railway

1. Go to https://railway.app
2. Sign up/login with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository
5. Railway auto-deploys! ⚡

## Step 3: Get Your URL

1. Click on your project → Click on the service
2. Go to **"Settings"** → **"Domains"**
3. Click **"Generate Domain"**
4. Copy the URL (e.g., `https://gumtree-scraper.up.railway.app`)

## Step 4: Add Environment Variables

In Railway: Project → Service → **"Variables"** tab

Add these variables:

```
SCRAPFLY_API_KEY=Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd
GUMTREE_EMAIL=pepeandamino@gmail.com
GUMTREE_PASSWORD=-trust555-
GOOGLE_SHEETS_ID=1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA
```

## Step 5: Handle Google Sheets Files

### Option A: Upload via Railway CLI (Easiest)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Upload credentials (from your project directory)
railway variables set GOOGLE_CREDENTIALS="$(cat credentials.json)"
railway variables set GOOGLE_TOKEN="$(cat token.json)"
```

Then update `data_handler.py` to read from environment variables if files don't exist.

### Option B: Use Railway Volume (Persistent Storage)

1. In Railway: Add **"Volume"** service
2. Mount it to `/app/data`
3. Upload `credentials.json` and `token.json` to the volume
4. Update paths in code to `/app/data/credentials.json`

### Option C: Skip Google Sheets for Now

If Google Sheets isn't critical, you can:
- Set `save_to_sheets: false` in API calls
- Data will still be returned as JSON in the API response

## Step 6: Update n8n Workflow

1. Go to https://sakib162.app.n8n.cloud/home/workflows
2. Open workflow → "Call Scraper API" node
3. Update URL to: `https://YOUR_RAILWAY_URL.railway.app/scrape`
4. Save and test!

## Step 7: Test

```bash
# Health check
curl https://YOUR_RAILWAY_URL.railway.app/health

# Test scrape
curl -X POST https://YOUR_RAILWAY_URL.railway.app/scrape \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 1, "max_listings": 2}'
```

## Done! 🎉

Your API now runs 24/7 in the cloud. You can:
- ✅ Stop your local server
- ✅ Stop localtunnel
- ✅ Use Railway URL in n8n.cloud

## Troubleshooting

**Deployment fails?**
- Check Railway logs: Service → "Deployments" → View logs
- Verify all files are in GitHub repo

**Environment variables not working?**
- Make sure they're added in Railway Variables tab
- Redeploy: "Deployments" → "Redeploy"

**Google Sheets not working?**
- Check Railway logs for file path errors
- Verify credentials files are accessible
- Consider using Option C (skip for now)

## Cost

- Free: $5 credit/month
- Paid: ~$5-10/month
- No credit card needed!

---

**Need help?** Check `RAILWAY_DEPLOYMENT_COMPLETE.md` for detailed instructions.

