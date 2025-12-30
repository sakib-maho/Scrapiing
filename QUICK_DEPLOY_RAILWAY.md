# Quick Deploy to Railway (5 minutes) 🚀

Railway is the easiest way to deploy your API server. **No credit card needed for free tier!**

## Step 1: Prepare Your Code

1. Make sure all your files are ready:
   - ✅ `api_server.py`
   - ✅ `requirements.txt`
   - ✅ `gumtree_scraper.py`
   - ✅ `data_handler.py`
   - ✅ `scrapfly_client.py`
   - ✅ `config.py`
   - ✅ `credentials.json` (for Google Sheets - if using)
   - ✅ `token.json` (for Google Sheets - if using)

## Step 2: Create GitHub Repository (if not already)

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/gumtree-scraper-api.git
git push -u origin main
```

**OR** if you already have a repo:
```bash
git add .
git commit -m "Add API server for n8n.cloud"
git push
```

## Step 3: Deploy to Railway

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub
5. Select your repository
6. Railway will auto-detect Python and start deploying!

## Step 4: Get Your URL

1. Once deployed, click on your project
2. Click on the service
3. Go to **"Settings"** → **"Domains"**
4. Railway gives you a free HTTPS URL like: `https://your-app.up.railway.app`
5. Copy this URL!

## Step 5: Set Environment Variables (if needed)

If your `config.py` uses environment variables:

1. In Railway, go to **"Variables"**
2. Add any needed variables (e.g., `SCRAPFLY_API_KEY`, etc.)

## Step 6: Update n8n.cloud Workflow

1. Go to https://sakib162.app.n8n.cloud/home/workflows
2. Open your workflow
3. Click on **"Call Scraper API"** node
4. Update the URL to: `https://your-app.up.railway.app/scrape`
5. Save and test!

## That's It! 🎉

Your API is now running 24/7 in the cloud. No need to keep your computer on!

## Monitoring

- View logs in Railway dashboard
- Check health: `https://your-app.up.railway.app/health`
- Railway auto-restarts if the app crashes

## Cost

- **Free tier:** $5 credit/month (usually enough for testing)
- **Paid:** ~$5-10/month for regular usage
- **No credit card needed** to start!

## Troubleshooting

**Deployment fails?**
- Check Railway logs
- Make sure all dependencies are in `requirements.txt`
- Verify `api_server.py` is in the root directory

**API not responding?**
- Check Railway logs for errors
- Verify the URL in n8n workflow
- Test health endpoint: `https://your-app.up.railway.app/health`

**Timeout errors?**
- Scraping can take time. Railway has a 60-second timeout by default
- Consider increasing timeout or optimizing scraper

