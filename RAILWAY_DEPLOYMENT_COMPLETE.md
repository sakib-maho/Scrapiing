# Complete Railway Deployment Guide 🚀

This guide will help you deploy your Gumtree Scraper API to Railway so it runs 24/7 in the cloud.

## Prerequisites

- GitHub account (free)
- Railway account (free tier available)
- Your project files ready

## Step 1: Prepare Your Code for Railway

### 1.1 Update Config to Use Environment Variables

Your `config.py` currently has hardcoded credentials. We need to update it to use environment variables for security.

**Important:** Don't commit sensitive credentials to GitHub!

### 1.2 Files Already Ready ✅

These files are already configured:
- ✅ `api_server.py` - Your Flask API
- ✅ `requirements.txt` - All dependencies including Flask & gunicorn
- ✅ `Procfile` - Tells Railway how to start the app
- ✅ `railway.json` - Railway-specific configuration
- ✅ `.gitignore` - Protects sensitive files

## Step 2: Create GitHub Repository

### 2.1 Initialize Git (if not already done)

```bash
cd "/Users/sakib/Salaheddine Mokhtari"

# Check if git is initialized
git status
```

If not initialized:
```bash
git init
git add .
git commit -m "Initial commit - Railway deployment ready"
```

### 2.2 Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `gumtree-scraper-api` (or any name you like)
3. Make it **Private** (recommended for security)
4. Don't initialize with README
5. Click "Create repository"

### 2.3 Push Your Code

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/gumtree-scraper-api.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**⚠️ Important:** Make sure `credentials.json` and `token.json` are in `.gitignore` (they already are!)

## Step 3: Deploy to Railway

### 3.1 Sign Up for Railway

1. Go to https://railway.app
2. Click "Start a New Project"
3. Sign up with GitHub (easiest way)

### 3.2 Deploy Your Project

1. In Railway dashboard, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub
4. Select your repository: `gumtree-scraper-api`
5. Railway will automatically:
   - Detect it's a Python project
   - Install dependencies from `requirements.txt`
   - Start the server using `Procfile`

### 3.3 Get Your Public URL

1. Once deployed, click on your project
2. Click on the service
3. Go to **"Settings"** tab
4. Scroll to **"Domains"** section
5. Click **"Generate Domain"**
6. Railway gives you a free HTTPS URL like: `https://your-app-name.up.railway.app`
7. **Copy this URL!** You'll need it for n8n

## Step 4: Configure Environment Variables

Your app needs sensitive credentials. Add them as environment variables in Railway:

### 4.1 In Railway Dashboard

1. Click on your project
2. Click on the service
3. Go to **"Variables"** tab
4. Click **"New Variable"**

### 4.2 Add These Variables

Add the following environment variables:

```
SCRAPFLY_API_KEY=Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd
GUMTREE_EMAIL=pepeandamino@gmail.com
GUMTREE_PASSWORD=-trust555-
GOOGLE_SHEETS_ID=1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA
```

**For Google Sheets credentials:**
- You'll need to upload `credentials.json` and `token.json` files
- See Step 5 below for how to handle this

### 4.3 Update config.py to Use Environment Variables

We need to update `config.py` to read from environment variables. Railway will automatically inject these.

**Note:** I'll create an updated version that uses environment variables with fallbacks.

## Step 5: Handle Google Sheets Credentials

### Option A: Upload Files via Railway CLI (Recommended)

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Link your project:
   ```bash
   railway link
   ```

4. Upload files:
   ```bash
   railway variables set GOOGLE_CREDENTIALS="$(cat credentials.json)"
   railway variables set GOOGLE_TOKEN="$(cat token.json)"
   ```

### Option B: Use Base64 Encoding

1. Encode files:
   ```bash
   base64 credentials.json > creds_base64.txt
   base64 token.json > token_base64.txt
   ```

2. Add as environment variables in Railway:
   - `GOOGLE_CREDENTIALS_B64` = (contents of creds_base64.txt)
   - `GOOGLE_TOKEN_B64` = (contents of token_base64.txt)

3. Update your code to decode them at runtime

### Option C: Store in Railway Volume (Advanced)

Railway supports persistent volumes. You can mount files there.

## Step 6: Update n8n.cloud Workflow

1. Go to https://sakib162.app.n8n.cloud/home/workflows
2. Open your workflow
3. Click on **"Call Scraper API"** node
4. Update the URL to your Railway URL:
   ```
   https://your-app-name.up.railway.app/scrape
   ```
5. Save the workflow
6. Test it!

## Step 7: Test Your Deployment

### 7.1 Test Health Endpoint

```bash
curl https://your-app-name.up.railway.app/health
```

Should return: `{"status": "healthy", "service": "Gumtree Scraper API"}`

### 7.2 Test Scrape Endpoint

```bash
curl -X POST https://your-app-name.up.railway.app/scrape \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 1, "max_listings": 2}'
```

## Troubleshooting

### Deployment Fails

- Check Railway logs: Click on your service → "Deployments" → View logs
- Verify `requirements.txt` has all dependencies
- Check that `api_server.py` is in the root directory

### Environment Variables Not Working

- Make sure variable names match exactly (case-sensitive)
- Redeploy after adding variables: Railway → "Deployments" → "Redeploy"

### Google Sheets Not Working

- Verify `credentials.json` and `token.json` are accessible
- Check file paths in your code
- Review Railway logs for errors

### API Timeout

- Scraping can take time. Railway has default timeout.
- The `railway.json` sets timeout to 300 seconds (5 minutes)
- If needed, increase in `railway.json`

## Cost

- **Free Tier:** $5 credit/month (usually enough for testing)
- **Paid:** ~$5-10/month for regular usage
- **No credit card needed** to start!

## Next Steps

1. ✅ Deploy to Railway
2. ✅ Set environment variables
3. ✅ Update n8n workflow with Railway URL
4. ✅ Test end-to-end
5. 🎉 Your scraper runs 24/7 in the cloud!

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

---

**You can now stop your local server and localtunnel!** Your API runs in the cloud 24/7! 🚀

