# VOTEGTR Analytics - Quick Start Guide

## Daily Commands

### View Dashboard
```bash
cd ~/votegtr-analytics
python3.10 cli.py dashboard
```

### Generate Report
```bash
python3.10 cli.py report daily --send-email
```

### Check Costs
```bash
python3.10 cli.py cost status
```

### Sync Data
```bash
python3.10 cli.py data sync --full
```

### Check System Health
```bash
python3.10 cli.py setup
```

## Add SendGrid API Key
```bash
# Edit .env file
nano .env
# Add: SENDGRID_API_KEY=SG.your_key_here

# Test email
python3.10 src/email_sender.py
```

## Manual GitHub Actions Trigger
1. Go to: https://github.com/SPMStrategies/votegtr-analytics/actions
2. Select "Daily Reports"
3. Click "Run workflow"

## Monitor Costs
- Daily limit: $5
- Monthly limit: $150
- Auto-shutoff if exceeded

## Support
- GitHub: https://github.com/SPMStrategies/votegtr-analytics
- Reports sent to: Sean@VOTEGTR.com
- Data source: GA4 Property 342478072

## Next Steps
1. Add SendGrid API key to .env file
2. Add SendGrid API key to GitHub Secrets
3. Daily reports will start tomorrow at 7AM ET
4. Monitor first few days to ensure everything works

---
System built with Claude - August 16, 2025