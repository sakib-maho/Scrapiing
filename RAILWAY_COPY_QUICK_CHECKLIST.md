# Railway Copy - Quick Checklist for n8n Setup

## 🚀 Quick Setup Steps

### 1. Deploy to Railway
- [ ] Create new Railway project
- [ ] Deploy from GitHub repo
- [ ] Get new Railway URL: `https://your-new-app.up.railway.app`

### 2. Set Environment Variables in Railway
Go to: **Railway Project → Service → Variables**

Add these variables:
- [ ] `SCRAPFLY_API_KEY` = `Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd`
- [ ] `GUMTREE_EMAIL` = `pepeandamino@gmail.com`
- [ ] `GUMTREE_PASSWORD` = `-trust555-`
- [ ] `GOOGLE_SHEETS_ID` = `1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA`

### 3. Upload Google Credentials (If Using Google Sheets)
- [ ] Upload `GOOGLE_CREDENTIALS` (full JSON from `credentials.json`)
- [ ] Upload `GOOGLE_TOKEN` (full JSON from `token.json`)
- [ ] **Redeploy** after adding variables

### 4. Update n8n Workflow
- [ ] Open workflow in n8n.cloud
- [ ] Click "Call Scraper API" node
- [ ] Update URL to: `https://your-new-app.up.railway.app/scrape`
- [ ] Save workflow

### 5. Test
- [ ] Test health: `curl https://your-new-app.up.railway.app/health`
- [ ] Test from n8n: Execute workflow
- [ ] Verify results appear

## ✅ What Stays the Same?

- ✅ All code files (no changes needed)
- ✅ `requirements.txt`
- ✅ `Procfile`
- ✅ `config.py` (uses environment variables)
- ✅ API endpoints (`/health` and `/scrape`)

## 🔄 What Changes?

- 🔄 **Railway URL** (unique for each deployment)
- 🔄 **Environment variables** (set in new Railway project)
- 🔄 **n8n workflow URL** (point to new Railway URL)

## 📝 Notes

- Each Railway deployment gets a unique URL
- Environment variables must be set in each new Railway project
- Google credentials must be uploaded to each new Railway project
- n8n workflow URL must be updated for each new Railway deployment

See `RAILWAY_COPY_SETUP.md` for detailed instructions.

