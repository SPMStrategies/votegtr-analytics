#!/bin/bash

# SendGrid Setup Script for VOTEGTR Analytics

echo "📧 SendGrid API Key Setup"
echo "========================"
echo ""
echo "Please enter your SendGrid API key (starts with 'SG.'):"
read -s SENDGRID_KEY
echo ""

# Update .env file
if [ ! -z "$SENDGRID_KEY" ]; then
    # Backup current .env
    cp .env .env.backup
    
    # Update the SendGrid key
    sed -i '' "s/SENDGRID_API_KEY=.*/SENDGRID_API_KEY=$SENDGRID_KEY/" .env
    
    echo "✅ SendGrid API key has been added to .env"
    echo ""
    echo "Testing email configuration..."
    python3.10 src/email_sender.py
else
    echo "❌ No API key entered"
fi