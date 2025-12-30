# Deployment Options for n8n.cloud Integration

You have several options to run the API server without keeping your computer on 24/7:

## Option 1: Railway.app (Easiest - Recommended) ⭐

**Free tier available, very easy setup**

1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Connect your repository (or create one with these files)
5. Railway auto-detects Python and installs dependencies
6. Set environment variables if needed
7. Deploy!

**Pros:**
- Free tier: $5 credit/month
- Auto-deploys from GitHub
- HTTPS included
- No credit card needed for free tier

**Cost:** Free for low usage, ~$5-10/month for regular use

---

## Option 2: Render.com

**Free tier available**

1. Go to https://render.com
2. Sign up
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python api_server.py` or `gunicorn -w 4 -b 0.0.0.0:$PORT api_server:app`
   - **Environment:** Python 3
6. Deploy!

**Pros:**
- Free tier available (spins down after inactivity)
- Auto-deploys from GitHub
- HTTPS included

**Cons:**
- Free tier spins down after 15 min inactivity (takes ~30 sec to wake up)

**Cost:** Free tier available, $7/month for always-on

---

## Option 3: Fly.io

**Free tier available**

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `fly auth signup`
3. In your project directory: `fly launch`
4. Follow prompts
5. Deploy: `fly deploy`

**Pros:**
- Free tier: 3 shared VMs
- Global edge network
- Very fast

**Cost:** Free for low usage

---

## Option 4: Heroku

**Paid only (no free tier anymore)**

1. Install Heroku CLI
2. `heroku create your-app-name`
3. `git push heroku main`
4. Set environment variables if needed

**Cost:** $5-7/month minimum

---

## Option 5: DigitalOcean App Platform

**Paid, but affordable**

1. Go to https://cloud.digitalocean.com
2. Create App Platform
3. Connect GitHub repo
4. Auto-detects Python

**Cost:** ~$5/month minimum

---

## Option 6: AWS Lambda (Serverless)

**Pay per request - very cheap for low usage**

Requires converting to serverless function. More complex setup.

**Cost:** Very cheap (~$0.20 per million requests)

---

## Option 7: Keep Local + Use ngrok (Temporary/Testing Only)

**Only for testing, not production**

- Your computer must be on
- Use ngrok to expose localhost
- Free but unreliable for production

**Cost:** Free but requires your computer running

---

## Recommended Setup

For **free/low cost**: Use **Railway** or **Render**
For **production**: Use **Railway** or **DigitalOcean**

## Quick Comparison

| Platform | Free Tier | Always On | Ease of Setup | Cost (Paid) |
|----------|-----------|-----------|---------------|-------------|
| Railway | ✅ $5 credit | ✅ | ⭐⭐⭐⭐⭐ | $5-10/mo |
| Render | ✅ (spins down) | ❌ Free | ⭐⭐⭐⭐ | $7/mo |
| Fly.io | ✅ | ✅ | ⭐⭐⭐ | Free |
| Heroku | ❌ | ✅ | ⭐⭐⭐ | $5-7/mo |
| DigitalOcean | ❌ | ✅ | ⭐⭐⭐⭐ | $5/mo |

---

## What You Need to Deploy

1. `api_server.py` - The Flask API
2. `requirements.txt` - Dependencies
3. `gumtree_scraper.py` - Your scraper
4. `data_handler.py` - Data handling
5. `scrapfly_client.py` - Scrapfly client
6. `config.py` - Configuration
7. `credentials.json` & `token.json` - Google Sheets auth (if using)

**Note:** You'll need to set environment variables or use a config file for sensitive data (API keys, etc.)

