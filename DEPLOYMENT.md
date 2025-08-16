# Deployment Guide

## GitHub Setup

### 1. Create GitHub Repository

```bash
# Create new repo on GitHub (via web interface)
# Name: votegtr-analytics

# Add remote to local repository
git remote add origin https://github.com/YOUR_USERNAME/votegtr-analytics.git

# Push initial code
git add .
git commit -m "Initial commit: VOTEGTR Analytics System"
git push -u origin main
```

### 2. Configure GitHub Secrets

Go to Settings → Secrets and variables → Actions, add:

- `GOOGLE_CREDENTIALS`: Your service account JSON (entire file contents)
- `GA4_PROPERTY_ID`: Your GA4 property ID
- `VERCEL_TOKEN`: Your Vercel API token
- `VERCEL_ORG_ID`: Your Vercel organization ID
- `VERCEL_PROJECT_ID`: Your Vercel project ID
- `SENDGRID_API_KEY`: For email reports
- `REPORT_EMAIL_TO`: Email recipient for reports

## Vercel Deployment

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Initial Deployment

```bash
# From project root
vercel

# Follow prompts:
# - Link to existing project? No
# - What's your project name? votegtr-analytics
# - In which directory is your code? ./
# - Want to override settings? No
```

### 3. Configure Environment Variables

```bash
# Add secrets to Vercel
vercel env add GOOGLE_CREDENTIALS_JSON
vercel env add GA4_PROPERTY_ID
vercel env add STRIPE_WEBHOOK_SECRET
vercel env add BIGQUERY_DATASET
```

### 4. Set Up Domains (Optional)

```bash
# Add custom domain
vercel domains add analytics.votegtr.com
```

## API Endpoints

Once deployed, your endpoints will be:

- **Webhook**: `https://votegtr-analytics.vercel.app/api/webhook`
  - Configure this in Stripe dashboard
  
- **Dashboard API**: `https://votegtr-analytics.vercel.app/api/dashboard/metrics`
  - Returns current metrics
  
- **Funnel API**: `https://votegtr-analytics.vercel.app/api/dashboard/funnel`
  - Returns funnel data
  
- **Real-time API**: `https://votegtr-analytics.vercel.app/api/dashboard/realtime`
  - Returns active users

## Stripe Webhook Configuration

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://votegtr-analytics.vercel.app/api/webhook`
3. Select events:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
4. Copy webhook signing secret
5. Add to Vercel env: `vercel env add STRIPE_WEBHOOK_SECRET`

## Monitoring

### GitHub Actions Status
- Check: https://github.com/YOUR_USERNAME/votegtr-analytics/actions

### Vercel Deployments
- Dashboard: https://vercel.com/YOUR_USERNAME/votegtr-analytics

### Logs
- Vercel Functions: `vercel logs`
- GitHub Actions: In Actions tab

## Troubleshooting

### Deployment Fails
1. Check GitHub Actions logs
2. Verify all secrets are set
3. Ensure credentials.json is valid

### Webhook Not Working
1. Check Vercel function logs: `vercel logs api/webhook.py`
2. Verify Stripe signature secret
3. Test with Stripe CLI: `stripe trigger checkout.session.completed`

### Reports Not Sending
1. Check GitHub Action schedule
2. Verify SendGrid API key
3. Check spam folder

## Updates

To deploy updates:

```bash
git add .
git commit -m "Update: description"
git push origin main
```

GitHub Actions will automatically deploy to Vercel.