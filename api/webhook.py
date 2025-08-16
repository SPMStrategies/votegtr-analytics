"""
Stripe Webhook Handler for Vercel
Receives purchase events and sends to BigQuery
"""

from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime
from google.cloud import bigquery
import hashlib
import hmac

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle Stripe webhook POST requests"""
        
        # Verify webhook signature
        stripe_signature = self.headers.get('Stripe-Signature')
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        # Read request body
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        
        # Verify signature (simplified - add full Stripe verification in production)
        if not self.verify_stripe_signature(body, stripe_signature, webhook_secret):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return
        
        # Parse event
        event = json.loads(body)
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            self.handle_purchase(event['data']['object'])
        elif event['type'] == 'payment_intent.succeeded':
            self.handle_payment(event['data']['object'])
        
        # Send success response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'received': True}).encode())
    
    def verify_stripe_signature(self, payload, signature, secret):
        """Verify Stripe webhook signature"""
        # Simplified verification - implement full Stripe signature verification
        return True  # TODO: Implement proper verification
    
    def handle_purchase(self, session):
        """Send purchase data to BigQuery"""
        try:
            # Initialize BigQuery client
            client = bigquery.Client()
            dataset_id = os.environ.get('BIGQUERY_DATASET', 'votegtr_analytics')
            table_id = f"{dataset_id}.purchases"
            
            # Prepare data
            row = {
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session.get('id'),
                'customer_email': session.get('customer_email'),
                'amount': session.get('amount_total', 0) / 100,  # Convert cents to dollars
                'currency': session.get('currency', 'usd'),
                'status': 'completed',
                'metadata': json.dumps(session.get('metadata', {}))
            }
            
            # Insert into BigQuery
            table = client.get_table(f"{client.project}.{table_id}")
            errors = client.insert_rows_json(table, [row])
            
            if errors:
                print(f"BigQuery insert errors: {errors}")
                
        except Exception as e:
            print(f"Error handling purchase: {e}")
    
    def handle_payment(self, payment_intent):
        """Handle payment success events"""
        # Similar to handle_purchase, customize as needed
        pass