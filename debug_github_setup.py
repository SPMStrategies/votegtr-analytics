#!/usr/bin/env python3
"""
Debug script to identify GitHub Actions setup issues
"""

import os
import sys
import json

def check_environment():
    """Check all required environment variables and files"""
    
    print("🔍 GitHub Actions Environment Check")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # Check required environment variables
    required_vars = {
        'GA4_PROPERTY_ID': '342478072',
        'SENDGRID_API_KEY': None,  # Any non-empty value
        'REPORT_EMAIL_TO': 'Sean@VOTEGTR.com'
    }
    
    print("\n📋 Environment Variables:")
    for var, expected in required_vars.items():
        value = os.getenv(var)
        if not value:
            print(f"  ❌ {var}: NOT SET")
            errors.append(f"{var} is not set")
        elif expected and value != expected:
            print(f"  ⚠️  {var}: {value} (expected: {expected})")
            warnings.append(f"{var} has unexpected value")
        else:
            # Mask sensitive values
            if 'KEY' in var or 'TOKEN' in var:
                print(f"  ✅ {var}: ***MASKED***")
            else:
                print(f"  ✅ {var}: {value}")
    
    # Check Google credentials
    print("\n📁 Files:")
    creds_path = 'config/credentials.json'
    if os.path.exists(creds_path):
        try:
            with open(creds_path, 'r') as f:
                creds = json.load(f)
                if 'type' in creds and creds['type'] == 'service_account':
                    print(f"  ✅ {creds_path}: Valid service account")
                else:
                    print(f"  ⚠️  {creds_path}: May not be valid service account")
                    warnings.append("Credentials file may be invalid")
        except json.JSONDecodeError:
            print(f"  ❌ {creds_path}: Invalid JSON")
            errors.append("Credentials file is not valid JSON")
    else:
        print(f"  ❌ {creds_path}: NOT FOUND")
        errors.append("Google credentials file not found")
    
    # Check Python packages
    print("\n📦 Python Packages:")
    required_packages = [
        'google-analytics-data',
        'google-cloud-bigquery',
        'sendgrid',
        'click',
        'pytz'
    ]
    
    import importlib
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}: NOT INSTALLED")
            errors.append(f"Package {package} not installed")
    
    # Summary
    print("\n" + "=" * 50)
    if errors:
        print("❌ ERRORS FOUND:")
        for error in errors:
            print(f"   - {error}")
        print("\n🔧 GitHub Secrets Required:")
        print("   1. GOOGLE_CREDENTIALS - Full service account JSON")
        print("   2. GA4_PROPERTY_ID - Should be: 342478072")
        print("   3. SENDGRID_API_KEY - Your SendGrid API key")
        print("   4. REPORT_EMAIL_TO - Should be: Sean@VOTEGTR.com")
        sys.exit(1)
    elif warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")
        sys.exit(0)
    else:
        print("✅ All checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    check_environment()