"""
Dashboard API endpoints for Vercel
Provides metrics data for web dashboards
"""

from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
from google.oauth2 import service_account

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for dashboard data"""
        
        # Enable CORS
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Parse endpoint
        path = self.path
        
        if '/metrics' in path:
            data = self.get_metrics()
        elif '/funnel' in path:
            data = self.get_funnel()
        elif '/realtime' in path:
            data = self.get_realtime()
        else:
            data = {'error': 'Unknown endpoint'}
        
        self.wfile.write(json.dumps(data).encode())
    
    def get_ga4_client(self):
        """Initialize GA4 client"""
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(os.environ.get('GOOGLE_CREDENTIALS_JSON')),
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        return BetaAnalyticsDataClient(credentials=credentials)
    
    def get_metrics(self):
        """Get basic metrics for dashboard"""
        try:
            client = self.get_ga4_client()
            property_id = os.environ.get('GA4_PROPERTY_ID')
            
            request = RunReportRequest(
                property=f"properties/{property_id}",
                dimensions=[Dimension(name="date")],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                    Metric(name="conversions")
                ],
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")]
            )
            
            response = client.run_report(request)
            
            # Format response
            data = {
                'metrics': {},
                'trend': []
            }
            
            for row in response.rows:
                date = row.dimension_values[0].value
                data['trend'].append({
                    'date': date,
                    'users': int(row.metric_values[0].value),
                    'sessions': int(row.metric_values[1].value),
                    'pageViews': int(row.metric_values[2].value),
                    'conversions': int(row.metric_values[3].value)
                })
            
            # Calculate totals
            if response.totals:
                totals = response.totals[0]
                data['metrics'] = {
                    'totalUsers': int(totals.metric_values[0].value),
                    'totalSessions': int(totals.metric_values[1].value),
                    'totalPageViews': int(totals.metric_values[2].value),
                    'totalConversions': int(totals.metric_values[3].value)
                }
            
            return data
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_funnel(self):
        """Get funnel data"""
        # Implementation for funnel metrics
        return {
            'stages': [
                {'name': 'Visitors', 'value': 1000},
                {'name': 'Engaged', 'value': 450},
                {'name': 'Form Submit', 'value': 87},
                {'name': 'Schedule', 'value': 23},
                {'name': 'Purchase', 'value': 5}
            ]
        }
    
    def get_realtime(self):
        """Get real-time active users"""
        try:
            client = self.get_ga4_client()
            property_id = os.environ.get('GA4_PROPERTY_ID')
            
            from google.analytics.data_v1beta.types import RunRealtimeReportRequest
            
            request = RunRealtimeReportRequest(
                property=f"properties/{property_id}",
                metrics=[Metric(name="activeUsers")]
            )
            
            response = client.run_realtime_report(request)
            
            active_users = 0
            if response.rows:
                active_users = int(response.rows[0].metric_values[0].value)
            
            return {'activeUsers': active_users}
            
        except Exception as e:
            return {'error': str(e), 'activeUsers': 0}