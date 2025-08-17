# GitHub Secrets Setup Guide

## Required GitHub Secrets

You need to add these secrets to your GitHub repository:

### 1. GOOGLE_CREDENTIALS (REQUIRED)
This must be the **complete** service account JSON file contents.

**How to add it correctly:**
1. Open your service account JSON file (`config/credentials.json`)
2. Copy the ENTIRE contents (including the curly braces)
3. Go to GitHub repository → Settings → Secrets and variables → Actions
4. Click "New repository secret"
5. Name: `GOOGLE_CREDENTIALS`
6. Value: Paste the entire JSON (should look like this):
```json
{
  "type": "service_account",
  "project_id": "votegtr-analytics",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 2. GA4_PROPERTY_ID
- Name: `GA4_PROPERTY_ID`
- Value: `342478072`

### 3. SENDGRID_API_KEY
- Name: `SENDGRID_API_KEY`
- Value: Your SendGrid API key (starts with `SG.`)

### 4. REPORT_EMAIL_TO
- Name: `REPORT_EMAIL_TO`
- Value: `Sean@VOTEGTR.com`

## Common Issues

### Issue: "GOOGLE_CREDENTIALS secret is empty or not set"
- The secret doesn't exist or is empty in GitHub
- Solution: Add the secret as shown above

### Issue: "Invalid JSON format"
- The JSON was not pasted correctly
- Common mistakes:
  - Only pasting part of the JSON
  - Missing opening or closing braces
  - Accidentally including extra text
- Solution: Copy and paste the ENTIRE file contents

### Issue: "Missing fields" or "Wrong credential type"
- You've pasted the wrong type of credentials
- Solution: Make sure you're using a service account JSON, not an API key or OAuth credentials

## How to Test
1. Go to Actions tab in GitHub
2. Click on "Daily Reports" workflow
3. Click "Run workflow"
4. Check the logs for any errors

## Verifying Your Service Account JSON
Run this locally to verify your JSON is correct:
```bash
python -c "
import json
with open('config/credentials.json') as f:
    data = json.load(f)
    print('Project ID:', data.get('project_id'))
    print('Client Email:', data.get('client_email'))
    print('Type:', data.get('type'))
    print('✓ Valid service account JSON')
"
```