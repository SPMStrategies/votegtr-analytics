#!/usr/bin/env python3
"""
Test script to verify GitHub Actions setup
"""

import os
import json
from datetime import datetime, timedelta
import pytz

def check_github_actions_status():
    """Check if GitHub Actions ran today at 7AM"""
    
    # Get New York timezone
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    
    # Calculate when 7AM ET was today
    seven_am_today = now.replace(hour=7, minute=0, second=0, microsecond=0)
    
    print("GitHub Actions Status Check")
    print("=" * 50)
    print(f"Current time (ET): {now.strftime('%Y-%m-%d %I:%M %p')}")
    print(f"Expected run time: {seven_am_today.strftime('%Y-%m-%d %I:%M %p')}")
    print()
    
    # Check for reports generated around 7AM
    reports_dir = "reports"
    if os.path.exists(reports_dir):
        files = sorted([f for f in os.listdir(reports_dir) if f.endswith('.json')])
        
        if files:
            latest_report = files[-1]
            # Extract timestamp from filename (e.g., daily_report_20250817_125301.json)
            parts = latest_report.split('_')
            if len(parts) >= 4:
                date_str = parts[2]
                time_str = parts[3].replace('.json', '')
                
                # Parse the timestamp
                report_time = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                report_time = ny_tz.localize(report_time)
                
                time_diff = abs((report_time - seven_am_today).total_seconds() / 60)
                
                print(f"📁 Latest report: {latest_report}")
                print(f"⏰ Generated at: {report_time.strftime('%Y-%m-%d %I:%M %p')}")
                print()
                
                if time_diff < 30:  # Within 30 minutes of 7AM
                    print("✅ GitHub Actions appears to have run successfully at 7AM!")
                else:
                    print("⚠️  No report found from 7AM today")
                    print(f"   Time difference: {time_diff:.0f} minutes")
    
    # Check configuration
    print("\n📋 Configuration Status:")
    print("-" * 30)
    
    # Check SendGrid
    sendgrid_key = os.getenv('SENDGRID_API_KEY', 'not_set')
    if sendgrid_key and sendgrid_key != 'your_sendgrid_key_here' and sendgrid_key != 'not_set':
        print("✅ SendGrid API key is configured")
    else:
        print("❌ SendGrid API key is NOT configured")
        print("   This prevents emails from being sent")
    
    # Check Google credentials
    if os.path.exists('config/credentials.json'):
        print("✅ Google credentials file exists")
    else:
        print("❌ Google credentials file missing")
    
    # Check GitHub workflow file
    workflow_file = '.github/workflows/daily-reports.yml'
    if os.path.exists(workflow_file):
        print("✅ GitHub Actions workflow file exists")
        
        # Check if the mkdir fix is in place
        with open(workflow_file, 'r') as f:
            content = f.read()
            if 'mkdir -p config' in content:
                print("✅ Config directory creation fix is in place")
            else:
                print("⚠️  Config directory creation fix may be missing")
    else:
        print("❌ GitHub Actions workflow file not found")
    
    print("\n📝 Summary:")
    print("-" * 30)
    print("The GitHub Actions workflow is configured to run at 7AM ET daily.")
    print("However, it requires the following in GitHub Secrets:")
    print("  - GOOGLE_CREDENTIALS (service account JSON)")
    print("  - GA4_PROPERTY_ID (342478072)")
    print("  - SENDGRID_API_KEY (for email delivery)")
    print("  - REPORT_EMAIL_TO (Sean@VOTEGTR.com)")
    print("\nThe fix for the config directory issue has been pushed to GitHub.")
    print("The workflow should run successfully tomorrow at 7AM ET if all")
    print("GitHub Secrets are properly configured.")

if __name__ == "__main__":
    check_github_actions_status()