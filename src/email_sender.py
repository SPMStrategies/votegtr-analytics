"""
Email Sender Module
Sends reports via SendGrid Web API
"""

import os
from typing import List, Optional
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, 
    Email, 
    To, 
    Content, 
    Attachment, 
    FileContent, 
    FileName,
    FileType,
    Disposition
)
import base64
from dotenv import load_dotenv

load_dotenv()


class EmailSender:
    """Handles email sending via SendGrid Web API"""
    
    def __init__(self):
        """Initialize SendGrid client"""
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('REPORT_EMAIL_FROM', 'reports@votegtr.com')
        self.default_to = os.getenv('REPORT_EMAIL_TO', 'Sean@VOTEGTR.com')
        
        if self.api_key and self.api_key != 'your_sendgrid_key_here':
            self.client = SendGridAPIClient(self.api_key)
            self.enabled = True
            print("✅ Email sender initialized with SendGrid Web API")
        else:
            self.enabled = False
            print("⚠️  SendGrid API key not configured - email sending disabled")
    
    def send_daily_report(self, html_content: str, json_path: Optional[str] = None, 
                         to_email: Optional[str] = None) -> bool:
        """
        Send daily report email
        
        Args:
            html_content: HTML content of the report
            json_path: Optional path to JSON file to attach
            to_email: Override recipient email
            
        Returns:
            Success status
        """
        if not self.enabled:
            print("📧 Email sending is disabled (no API key)")
            return False
        
        try:
            # Prepare email
            to_email = to_email or self.default_to
            subject = f"VOTEGTR Daily Report - {datetime.now().strftime('%B %d, %Y')}"
            
            # Create message
            message = Mail(
                from_email=Email(self.from_email, "VOTEGTR Analytics"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            # Add JSON attachment if provided
            if json_path and os.path.exists(json_path):
                with open(json_path, 'rb') as f:
                    data = f.read()
                encoded = base64.b64encode(data).decode()
                
                attachment = Attachment()
                attachment.file_content = FileContent(encoded)
                attachment.file_type = FileType('application/json')
                attachment.file_name = FileName(f'report_{datetime.now().strftime("%Y%m%d")}.json')
                attachment.disposition = Disposition('attachment')
                
                message.attachment = attachment
            
            # Send email
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Report email sent to {to_email}")
                return True
            else:
                print(f"❌ Failed to send email: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def send_alert(self, alert_type: str, message: str, severity: str = 'warning',
                  to_email: Optional[str] = None) -> bool:
        """
        Send alert email
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (info, warning, critical)
            to_email: Override recipient
            
        Returns:
            Success status
        """
        if not self.enabled:
            return False
        
        try:
            to_email = to_email or self.default_to
            
            # Severity emoji
            severity_emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'critical': '🚨',
                'emergency': '🆘'
            }
            
            emoji = severity_emoji.get(severity, '📢')
            subject = f"{emoji} VOTEGTR Alert: {alert_type}"
            
            # HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        padding: 20px;
                        background: #f5f5f5;
                    }}
                    .alert-box {{
                        background: white;
                        border-radius: 8px;
                        padding: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        border-left: 4px solid {'#dc3545' if severity == 'critical' else '#ffc107'};
                    }}
                    .alert-type {{
                        color: #666;
                        font-size: 14px;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}
                    .alert-message {{
                        font-size: 18px;
                        margin: 15px 0;
                        color: #333;
                    }}
                    .timestamp {{
                        color: #999;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="alert-box">
                    <div class="alert-type">{severity.upper()} ALERT</div>
                    <h2>{alert_type}</h2>
                    <div class="alert-message">{message}</div>
                    <div class="timestamp">Generated at {datetime.now().strftime('%I:%M %p on %B %d, %Y')}</div>
                </div>
                <p style="margin-top: 20px; color: #666; font-size: 14px;">
                    Check your dashboard for more details: <a href="https://votegtr.com">VOTEGTR Analytics</a>
                </p>
            </body>
            </html>
            """
            
            # Create and send message
            message = Mail(
                from_email=Email(self.from_email, "VOTEGTR Alerts"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Alert email sent to {to_email}")
                return True
            else:
                print(f"❌ Failed to send alert: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending alert: {e}")
            return False
    
    def send_test_email(self, to_email: Optional[str] = None) -> bool:
        """
        Send test email to verify configuration
        
        Args:
            to_email: Override recipient
            
        Returns:
            Success status
        """
        if not self.enabled:
            print("❌ Cannot send test email - SendGrid not configured")
            print("   Please add your SendGrid API key to .env file")
            return False
        
        try:
            to_email = to_email or self.default_to
            
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    .success { color: #28a745; }
                </style>
            </head>
            <body>
                <h1 class="success">✅ SendGrid Test Successful!</h1>
                <p>Your VOTEGTR Analytics email configuration is working correctly.</p>
                <ul>
                    <li>From: reports@votegtr.com</li>
                    <li>To: Sean@VOTEGTR.com</li>
                    <li>API: SendGrid Web API</li>
                    <li>Status: Active</li>
                </ul>
                <p>You will receive daily reports at 7AM ET to this email address.</p>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=Email(self.from_email, "VOTEGTR Analytics"),
                to_emails=To(to_email),
                subject="VOTEGTR Analytics - Test Email",
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Test email sent successfully to {to_email}")
                print("   Check your inbox to confirm delivery")
                return True
            else:
                print(f"❌ Test email failed: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending test email: {e}")
            print(f"   Make sure your SendGrid API key is valid")
            return False


if __name__ == "__main__":
    # Test email sender
    sender = EmailSender()
    
    print("\n📧 Testing Email Sender...")
    print("-" * 50)
    
    if sender.enabled:
        print("\nSending test email...")
        success = sender.send_test_email()
        
        if success:
            print("\n✅ Email system ready!")
            print(f"   Reports will be sent to: {sender.default_to}")
        else:
            print("\n❌ Email test failed")
            print("   Please check your SendGrid API key")
    else:
        print("\n⚠️  To enable email reports:")
        print("   1. Get your SendGrid API key from: https://app.sendgrid.com/settings/api_keys")
        print("   2. Add it to .env file: SENDGRID_API_KEY=your_actual_key")
        print("   3. Run this test again")