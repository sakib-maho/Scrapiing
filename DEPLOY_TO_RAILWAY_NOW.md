# 🚀 Deploy to Railway - Step by Step

## ✅ What's Already Ready

Your project is already configured for Railway:
- ✅ `api_server.py` - Flask API server
- ✅ `requirements.txt` - All dependencies
- ✅ `Procfile` - Startup command
- ✅ `railway.json` - Railway config
- ✅ `config.py` - Updated to use environment variables
- ✅ `.gitignore` - Protects sensitive files

## 📋 Quick Deployment Steps

### 1. Push to GitHub (5 minutes)

```bash
cd "/Users/sakib/Salaheddine Mokhtari"

# Initialize git if needed
git init
git add .
git commit -m "Ready for Railway"

# Create repo on GitHub.com (make it private!)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/gumtree-scraper-api.git
git branch -M main
git push -u origin main
```

### 2. Deploy to Railway (2 minutes)

1. Go to **https://railway.app**
2. Sign up with **GitHub**
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository
5. **Wait for deployment** (takes 2-3 minutes)

### 3. Get Your URL (1 minute)

1. Click on your project
2. Click on the service
3. **Settings** → **Domains** → **Generate Domain**
4. Copy URL: `https://your-app.up.railway.app`

### 4. Add Environment Variables (2 minutes)

In Railway: **Project** → **Service** → **Variables** tab

Click **"New Variable"** and add:

| Variable Name | Value |
|--------------|-------|
| `SCRAPFLY_API_KEY` | `Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd` |
| `GUMTREE_EMAIL` | `pepeandamino@gmail.com` |
| `GUMTREE_PASSWORD` | `-trust555-` |
| `GOOGLE_SHEETS_ID` | `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA` |

### 5. Handle Google Credentials (Optional - 5 minutes)

**Option A: Upload via Railway CLI** (Recommended)

```bash
npm install -g @railway/cli
railway login
railway link
railway variables set GOOGLE_CREDENTIALS="$(cat credentials.json)"
railway variables set GOOGLE_TOKEN="$(cat token.json)"
```

**Option B: Skip for Now**

- Google Sheets will fail, but API will still return JSON data
- You can add credentials later

### 6. Update n8n Workflow (1 minute)

1. Go to **https://sakib162.app.n8n.cloud/home/workflows**
2. Open workflow
3. Click **"Call Scraper API"** node
4. Change URL to: `https://YOUR_RAILWAY_URL.railway.app/scrape`
5. **Save**

### 7. Test! (1 minute)

```bash
# Health check
curl https://YOUR_RAILWAY_URL.railway.app/health

# Should return: {"status": "healthy", "service": "Gumtree Scraper API"}
```

## 🎉 Done!

Your API is now running 24/7 in the cloud!

## 📝 Important Notes

- **Stop local server** - You don't need it anymore
- **Stop localtunnel** - Railway provides HTTPS
- **Keep Railway running** - It runs 24/7 automatically
- **Free tier:** $5 credit/month (usually enough)

## 🔧 Troubleshooting

**Deployment fails?**
- Check Railway logs: Service → Deployments → View logs
- Make sure all files are in GitHub

**Environment variables?**
- Add them in Railway Variables tab
- Redeploy after adding: Deployments → Redeploy

**Google Sheets not working?**
- Check Railway logs
- Upload credentials via Railway CLI (Step 5)
- Or skip Google Sheets for now

## 📚 More Help

- **Detailed guide:** `RAILWAY_DEPLOYMENT_COMPLETE.md`
- **Quick reference:** `RAILWAY_QUICK_START.md`
- **Railway docs:** https://docs.railway.app

---

**Total time: ~15 minutes** ⚡

