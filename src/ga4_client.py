"""
GA4 API Client Module
Handles all interactions with Google Analytics 4 API
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    RunRealtimeReportRequest,
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    FilterExpression,
    Filter
)
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()


class GA4Client:
    """Client for interacting with GA4 API"""
    
    def __init__(self, property_id: Optional[str] = None):
        """
        Initialize GA4 client
        
        Args:
            property_id: GA4 property ID (optional, can use env var)
        """
        self.property_id = property_id or os.getenv('GA4_PROPERTY_ID')
        if not self.property_id:
            raise ValueError("GA4_PROPERTY_ID not found in environment or parameters")
        
        # Initialize credentials
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found in environment")
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        self.client = BetaAnalyticsDataClient(credentials=credentials)
        print(f"✅ GA4 Client initialized for property: {self.property_id}")
    
    def get_funnel_metrics(self, start_date: str = '7daysAgo', end_date: str = 'today') -> Dict:
        """
        Get funnel metrics based on VOTEGTR's conversion stages
        
        Returns dict with funnel stage data
        """
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="date")
            ],
            metrics=[
                Metric(name="eventCount"),
                Metric(name="totalUsers")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)]
        )
        
        response = self.client.run_report(request)
        
        # Define funnel events
        funnel_events = {
            'page_view': {'stage': 'Awareness', 'count': 0, 'users': 0},
            'scroll': {'stage': 'Engagement', 'count': 0, 'users': 0},
            'blog_read': {'stage': 'Consideration', 'count': 0, 'users': 0},
            'start_now_clicked': {'stage': 'Interest', 'count': 0, 'users': 0},
            'form_submit': {'stage': 'Lead Capture', 'count': 0, 'users': 0},
            'click_call_now': {'stage': 'High Intent', 'count': 0, 'users': 0},
            'click_schedule_time': {'stage': 'Qualified Lead', 'count': 0, 'users': 0},
            'purchase_completed': {'stage': 'Purchase', 'count': 0, 'users': 0}
        }
        
        # Parse response
        for row in response.rows:
            event_name = row.dimension_values[0].value
            if event_name in funnel_events:
                funnel_events[event_name]['count'] += int(row.metric_values[0].value)
                funnel_events[event_name]['users'] += int(row.metric_values[1].value)
        
        # Build funnel stages
        funnel_stages = []
        for event, data in funnel_events.items():
            if data['count'] > 0:
                funnel_stages.append({
                    'event': event,
                    'stage': data['stage'],
                    'count': data['count'],
                    'users': data['users'],
                    'conversion_rate': 0  # Will calculate after sorting
                })
        
        # Sort by count (descending) to calculate conversion rates
        funnel_stages.sort(key=lambda x: x['count'], reverse=True)
        
        # Calculate conversion rates
        if funnel_stages:
            for i, stage in enumerate(funnel_stages):
                if i == 0:
                    stage['conversion_rate'] = 100.0
                else:
                    stage['conversion_rate'] = (stage['count'] / funnel_stages[0]['count']) * 100
        
        return {
            'stages': funnel_stages,
            'date_range': f"{start_date} to {end_date}",
            'total_visitors': funnel_stages[0]['users'] if funnel_stages else 0
        }
    
    def get_attribution_data(self, start_date: str = '7daysAgo', end_date: str = 'today') -> Dict:
        """
        Get attribution data showing traffic sources and conversion paths
        """
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
                Dimension(name="sessionCampaignName")
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="conversions"),
                Metric(name="screenPageViews")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                    desc=True
                )
            ],
            limit=20
        )
        
        response = self.client.run_report(request)
        
        attribution_data = []
        total_conversions = 0
        
        for row in response.rows:
            source = row.dimension_values[0].value or '(not set)'
            medium = row.dimension_values[1].value or '(not set)'
            campaign = row.dimension_values[2].value or '(not set)'
            
            sessions = int(row.metric_values[0].value)
            users = int(row.metric_values[1].value)
            conversions = int(row.metric_values[2].value)
            page_views = int(row.metric_values[3].value)
            
            total_conversions += conversions
            
            attribution_data.append({
                'source': source,
                'medium': medium,
                'campaign': campaign,
                'channel': f"{source}/{medium}",
                'sessions': sessions,
                'users': users,
                'conversions': conversions,
                'page_views': page_views,
                'conversion_rate': (conversions / sessions * 100) if sessions > 0 else 0,
                'pages_per_session': page_views / sessions if sessions > 0 else 0
            })
        
        # Calculate UTM coverage
        utm_sessions = sum(d['sessions'] for d in attribution_data 
                          if d['source'] != '(not set)' and d['source'] != '(direct)')
        total_sessions = sum(d['sessions'] for d in attribution_data)
        utm_coverage = (utm_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        return {
            'channels': attribution_data,
            'total_conversions': total_conversions,
            'utm_coverage': utm_coverage,
            'date_range': f"{start_date} to {end_date}"
        }
    
    def get_real_time_users(self) -> Dict:
        """
        Get real-time active users on the site
        """
        request = RunRealtimeReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="country"),
                Dimension(name="deviceCategory"),
                Dimension(name="unifiedScreenName")
            ],
            metrics=[
                Metric(name="activeUsers")
            ]
        )
        
        response = self.client.run_realtime_report(request)
        
        total_users = 0
        by_country = {}
        by_device = {}
        by_page = {}
        
        for row in response.rows:
            country = row.dimension_values[0].value
            device = row.dimension_values[1].value
            page = row.dimension_values[2].value
            users = int(row.metric_values[0].value)
            
            total_users += users
            
            by_country[country] = by_country.get(country, 0) + users
            by_device[device] = by_device.get(device, 0) + users
            by_page[page] = by_page.get(page, 0) + users
        
        return {
            'total_active_users': total_users,
            'by_country': dict(sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:5]),
            'by_device': by_device,
            'by_page': dict(sorted(by_page.items(), key=lambda x: x[1], reverse=True)[:5]),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_daily_metrics(self, days: int = 7) -> Dict:
        """
        Get daily metrics for the past N days
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = 'today'
        
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="conversions")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            order_bys=[
                OrderBy(
                    dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
                    desc=False
                )
            ]
        )
        
        response = self.client.run_report(request)
        
        daily_data = []
        for row in response.rows:
            date = row.dimension_values[0].value
            daily_data.append({
                'date': date,
                'users': int(row.metric_values[0].value),
                'sessions': int(row.metric_values[1].value),
                'page_views': int(row.metric_values[2].value),
                'avg_session_duration': float(row.metric_values[3].value),
                'bounce_rate': float(row.metric_values[4].value) * 100,
                'conversions': int(row.metric_values[5].value)
            })
        
        # Calculate totals
        totals = {
            'total_users': sum(d['users'] for d in daily_data),
            'total_sessions': sum(d['sessions'] for d in daily_data),
            'total_page_views': sum(d['page_views'] for d in daily_data),
            'total_conversions': sum(d['conversions'] for d in daily_data),
            'avg_bounce_rate': sum(d['bounce_rate'] for d in daily_data) / len(daily_data) if daily_data else 0
        }
        
        return {
            'daily_metrics': daily_data,
            'totals': totals,
            'period': f"Last {days} days"
        }
    
    def get_top_pages(self, start_date: str = '7daysAgo', end_date: str = 'today', limit: int = 10) -> List[Dict]:
        """
        Get top performing pages
        """
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="pagePath"),
                Dimension(name="pageTitle")
            ],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="totalUsers"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                    desc=True
                )
            ],
            limit=limit
        )
        
        response = self.client.run_report(request)
        
        pages = []
        for row in response.rows:
            pages.append({
                'path': row.dimension_values[0].value,
                'title': row.dimension_values[1].value,
                'views': int(row.metric_values[0].value),
                'users': int(row.metric_values[1].value),
                'avg_time': float(row.metric_values[2].value),
                'bounce_rate': float(row.metric_values[3].value) * 100
            })
        
        return pages
    
    def check_data_quality(self) -> Dict:
        """
        Check data quality and identify issues
        """
        # Get recent events to check for issues
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="sessionSource")
            ],
            metrics=[
                Metric(name="eventCount")
            ],
            date_ranges=[DateRange(start_date="yesterday", end_date="today")]
        )
        
        response = self.client.run_report(request)
        
        # Check for key events
        expected_events = ['form_submit', 'click_call_now', 'click_schedule_time', 'page_view']
        found_events = set()
        unattributed_count = 0
        total_events = 0
        
        for row in response.rows:
            event_name = row.dimension_values[0].value
            source = row.dimension_values[1].value
            count = int(row.metric_values[0].value)
            
            found_events.add(event_name)
            total_events += count
            
            if source == '(not set)':
                unattributed_count += count
        
        missing_events = [e for e in expected_events if e not in found_events]
        attribution_rate = ((total_events - unattributed_count) / total_events * 100) if total_events > 0 else 0
        
        return {
            'status': 'healthy' if not missing_events and attribution_rate > 75 else 'warning',
            'missing_events': missing_events,
            'attribution_rate': attribution_rate,
            'total_events_24h': total_events,
            'issues': []
        }
        
        if missing_events:
            issues.append(f"Missing events: {', '.join(missing_events)}")
        if attribution_rate < 75:
            issues.append(f"Low attribution rate: {attribution_rate:.1f}%")
        
        return {
            'status': 'healthy' if not issues else 'warning',
            'missing_events': missing_events,
            'attribution_rate': attribution_rate,
            'total_events_24h': total_events,
            'issues': issues
        }


if __name__ == "__main__":
    # Test the client
    try:
        client = GA4Client()
        
        print("\n📊 Testing GA4 Client...")
        print("-" * 50)
        
        # Test real-time users
        print("\n👥 Real-time Users:")
        realtime = client.get_real_time_users()
        print(f"Active users now: {realtime['total_active_users']}")
        
        # Test daily metrics
        print("\n📈 Daily Metrics (Last 7 days):")
        metrics = client.get_daily_metrics(7)
        print(f"Total sessions: {metrics['totals']['total_sessions']}")
        print(f"Total conversions: {metrics['totals']['total_conversions']}")
        
        # Test funnel
        print("\n🔄 Funnel Metrics:")
        funnel = client.get_funnel_metrics()
        for stage in funnel['stages'][:3]:
            print(f"  {stage['stage']}: {stage['count']} events ({stage['conversion_rate']:.1f}%)")
        
        print("\n✅ GA4 Client test successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")