# VOTEGTR Analytics Management System

Automated analytics pipeline for VOTEGTR.com, integrating GA4, BigQuery, and automated reporting.

## Features

- 📊 Real-time GA4 data extraction
- 💾 BigQuery data warehouse integration
- 📧 Automated daily reports (7AM ET)
- 🚨 Intelligent alert system
- 📈 Looker Studio dashboards
- 🔧 CLI tools for data queries

## Setup

### 1. Prerequisites
- Google Cloud Project with enabled APIs (Analytics Data, BigQuery)
- GA4 property with service account access
- Python 3.9+

### 2. Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/votegtr-analytics.git
cd votegtr-analytics

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 3. Configuration

1. Place your Google Cloud credentials JSON in `config/credentials.json`
2. Update `.env` with your GA4 property ID and other settings
3. Run initial setup: `python cli.py setup`

## Usage

### CLI Commands

```bash
# View real-time dashboard
python cli.py dashboard

# Generate daily report
python cli.py report daily

# Check funnel performance
python cli.py funnel --yesterday

# Run system health check
python cli.py health
```

### Automated Reports

Reports are automatically generated and sent at 7AM ET daily. Configure recipients in `.env`.

## Architecture

```
GA4 → API → BigQuery → Processing → Reports/Dashboards
                    ↓
              Stripe Webhook
```

## Deployment

### Vercel (Web Dashboard)
The web dashboard component can be deployed to Vercel:

```bash
vercel deploy
```

### Cloud Functions (Automation)
Automated tasks run on Google Cloud Functions, deployed via:

```bash
python deploy.py
```

## Support

For issues or questions, contact [your-email]

## License

Private - VOTEGTR Proprietary