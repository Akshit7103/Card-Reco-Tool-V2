# Deployment Guide - Render

This guide will help you deploy the Card Reconciliation Tool to Render.

## Prerequisites

- Render account (sign up at https://render.com - free tier available)
- OpenAI API key (get from https://platform.openai.com/api-keys)
- This repository pushed to GitHub

## Quick Deploy Steps

### 1. Prepare API Keys

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Name it `Card-Reco-Tool-Production`
4. Copy the key (you can't see it again!)

**Flask Secret Key:**
Generate a secure random key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Create Web Service on Render

1. Log in to Render: https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `Card-Reco-Tool-V2`
4. Configure the service:

**Basic Settings:**
- **Name:** `card-reconciliation-tool` (or your preferred name)
- **Region:** Choose closest to you
- **Branch:** `main`
- **Runtime:** `Python 3`

**Build & Deploy:**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`

**Instance Type:**
- Select **"Free"** (or "Starter" for $7/month)

### 3. Set Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

**Required Variables:**
```
OPENAI_API_KEY = your_openai_api_key_here
SECRET_KEY = your_generated_secret_key_here
```

**Optional Variables (email alerts - already in code):**
```
SMTP_HOST = smtp.mailjet.com
SMTP_PORT = 587
SMTP_USER = your_mailjet_api_key
SMTP_PASS = your_mailjet_secret_key
EMAIL_SENDER = your_email@example.com
EMAIL_RECIPIENT = recipient_email@example.com
```

### 4. Deploy!

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start your application
3. First deployment takes ~5-10 minutes
4. You'll get a URL like: `https://card-reconciliation-tool.onrender.com`

## Post-Deployment Testing

### Basic Test
1. Visit your Render URL
2. Go to "Rates File" → "Manual Upload"
3. Upload a summary file
4. Verify results display correctly

### Full Test
1. Go to "Automated Batch" tab
2. Upload a ZIP file with transactions
3. Watch processing page
4. View detailed results for each transaction
5. Verify root cause analysis appears (for < 95% reconciliation)

## Free Tier Limitations

- **Sleeps after 15 minutes** of inactivity
  - First request after sleep: ~30 seconds to wake up
  - Subsequent requests: Fast
  
- **512 MB RAM**
  - Sufficient for most use cases
  
- **Shared CPU**
  - May be slower for large files

## Upgrading to Starter Tier ($7/month)

Benefits:
- No sleep (always available)
- Better performance
- Faster processing

To upgrade:
1. Go to your service in Render dashboard
2. Click "Settings"
3. Change "Instance Type" to "Starter"
4. Save changes

## Monitoring

**View Logs:**
- Render Dashboard → Your Service → "Logs" tab
- See real-time application output
- Debug errors and API calls

**Monitor API Usage:**
- OpenAI Dashboard: https://platform.openai.com/usage
- Track costs (~$0.20-$2/month typical)

## Troubleshooting

### "Application Error"
- Check logs in Render dashboard
- Verify environment variables are set correctly
- Ensure dependencies installed successfully

### Root Cause Analysis Not Working
- Verify `OPENAI_API_KEY` is set
- Check OpenAI API key is valid and has credits
- Look for API errors in logs

### Email Alerts Not Sending
- Verify Mailjet credentials
- Check sender email is verified on Mailjet
- Review SMTP errors in logs

## Security Notes

- ✅ API keys are in environment variables (not in code)
- ✅ No sensitive data committed to GitHub
- ✅ HTTPS automatic on Render
- ✅ Sessions use secure secret key

## Support

For Render-specific issues:
- Render Docs: https://render.com/docs
- Render Community: https://community.render.com

For application issues:
- Check logs first
- Review error messages
- Verify all environment variables set

## Cost Estimate

**Free Tier:**
- Render: $0/month
- OpenAI API: ~$0.20-$2/month
- **Total: ~$0.20-$2/month**

**Starter Tier:**
- Render: $7/month
- OpenAI API: ~$0.20-$2/month
- **Total: ~$7.20-$9/month**

---

**Deployment Date:** 2025
**Status:** ✅ Production Ready
**Environment:** Render Free/Starter Tier
