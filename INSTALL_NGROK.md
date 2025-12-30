# Install ngrok - Quick Guide

Your API server is working! ✅ Now you need ngrok to expose it to n8n.cloud.

## Option 1: Install ngrok via Homebrew (Recommended)

Run this in your terminal:
```bash
brew install ngrok/ngrok/ngrok
```

If you get permission errors, you may need to run:
```bash
sudo chown -R $(whoami) /opt/homebrew/Cellar
brew install ngrok/ngrok/ngrok
```

## Option 2: Download ngrok Directly (Easier)

1. Go to: https://ngrok.com/download
2. Download for macOS
3. Unzip the file
4. Move it to a location in your PATH:
   ```bash
   sudo mv ngrok /usr/local/bin/
   ```
   OR add it to your current directory and use: `./ngrok`

## Option 3: Use localtunnel (Alternative - No Install Needed)

If you have Node.js installed, you can use localtunnel instead:

```bash
# Install localtunnel globally
npm install -g localtunnel

# Then use it instead of ngrok
lt --port 5001
```

## After Installation

Once ngrok is installed, run:
```bash
ngrok http 5001
```

You'll see output like:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:5001
```

Copy the HTTPS URL and use it in your n8n.cloud workflow!

## Quick Test

After starting ngrok, test it:
```bash
curl https://YOUR_NGROK_URL.ngrok.io/health
```

Should return the same health check response.

