"""
GA4 Data Collector
Pulls comprehensive daily data from GA4 API
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ga4_client import GA4Client

class GA4DataCollector:
    """Collects all GA4 data for daily storage"""

    def __init__(self):
        self.ga4 = GA4Client()
        print("✅ GA4 Data Collector initialized")

    def collect_daily_data(self, date: str = 'yesterday') -> Dict:
        """
        Pull all GA4 data for a specific date

        Args:
            date: 'yesterday', 'today', or 'YYYY-MM-DD'

        Returns:
            Dict with all collected data
        """
        print(f"\n📊 Collecting GA4 data for {date}...")

        # Convert date to GA4 format
        if date == 'yesterday':
            ga4_date = 'yesterday'
            actual_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif date == 'today':
            ga4_date = 'today'
            actual_date = datetime.now().strftime('%Y-%m-%d')
        else:
            # Calculate days ago
            target = datetime.strptime(date, '%Y-%m-%d')
            today = datetime.now()
            days_ago = (today - target).days
            ga4_date = f'{days_ago}daysAgo'
            actual_date = date

        data = {
            'metadata': {
                'collection_date': datetime.now().isoformat(),
                'data_date': actual_date
            },
            'funnel_performance': self.ga4.get_funnel_metrics(ga4_date, ga4_date),
            'traffic_sources': self.ga4.get_attribution_data(ga4_date, ga4_date),
            'page_performance': self.ga4.get_top_pages(limit=50),
            'daily_metrics': self.ga4.get_daily_metrics(days=1)
        }

        print("✅ Data collection complete")
        return data
