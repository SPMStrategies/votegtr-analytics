"""
Data Organizer
Manages date-stamped data folders
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

class DataOrganizer:
    """Organizes analytics data into date-stamped folders"""

    def __init__(self):
        self.base_dir = Path('data')
        self.base_dir.mkdir(exist_ok=True)
        print("✅ Data Organizer initialized")

    def save_daily_data(self, date: str, data: Dict):
        """
        Save data to data/YYYY-MM-DD/ folder

        Args:
            date: Date string (YYYY-MM-DD)
            data: Dict of collected data
        """
        folder = self.base_dir / date
        folder.mkdir(exist_ok=True)

        print(f"📁 Saving data to {folder}/")

        for key, content in data.items():
            if key == 'metadata':
                continue

            filename = f"{key}.json"
            filepath = folder / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, default=str)

            print(f"  ✓ Saved {filename}")

        print(f"✅ Data saved to {folder}")

    def get_week_data(self, end_date: str) -> Dict:
        """
        Aggregate 7 days of data ending on end_date

        Args:
            end_date: End date (YYYY-MM-DD)

        Returns:
            Aggregated week data
        """
        end = datetime.strptime(end_date, '%Y-%m-%d')
        dates = [(end - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        dates.reverse()  # Chronological order

        print(f"\n📅 Aggregating data for week: {dates[0]} to {dates[-1]}")

        week_data = {
            'date_range': f"{dates[0]} to {dates[-1]}",
            'dates': dates,
            'funnel': self._aggregate_funnels(dates),
            'conversions': self._aggregate_conversions(dates),
            'traffic': self._aggregate_traffic(dates),
            'pages': self._aggregate_pages(dates),
            'devices': {}  # Placeholder for device data
        }

        return week_data

    def _aggregate_funnels(self, dates: List[str]) -> Dict:
        """Aggregate funnel data across dates"""
        funnel_stages = {}
        total_sessions = 0

        for date in dates:
            filepath = self.base_dir / date / 'funnel_performance.json'
            if not filepath.exists():
                continue

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Aggregate funnel stages
            for stage in data.get('funnel_stages', []):
                event = stage['event']
                if event not in funnel_stages:
                    funnel_stages[event] = {
                        'stage': stage['stage'],
                        'count': 0,
                        'users': set()
                    }
                funnel_stages[event]['count'] += stage['count']

            total_sessions += data.get('total_sessions', 0)

        # Convert to list with progression rates
        stages_list = []
        previous_count = None
        ordered_stages = ['session_start', 'page_view', 'user_engagement', 'click']

        for event in ordered_stages:
            if event in funnel_stages:
                data = funnel_stages[event]
                count = data['count']

                if previous_count is not None and previous_count > 0:
                    progression = round((count / previous_count) * 100, 1)
                    drop_off = round(100 - progression, 1)
                else:
                    progression = 100.0
                    drop_off = 0.0

                stages_list.append({
                    'event': event,
                    'stage': data['stage'],
                    'count': count,
                    'users': count,  # Approximation
                    'progression_rate': progression,
                    'drop_off_rate': drop_off
                })

                previous_count = count

        return {
            'funnel_stages': stages_list,
            'total_sessions': total_sessions
        }

    def _aggregate_conversions(self, dates: List[str]) -> Dict:
        """Aggregate conversion data"""
        conversion_events = {}
        total_conversions = 0

        for date in dates:
            filepath = self.base_dir / date / 'funnel_performance.json'
            if not filepath.exists():
                continue

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Aggregate conversions
            for conv in data.get('conversions', {}).get('events', []):
                event = conv['event']
                if event not in conversion_events:
                    conversion_events[event] = {
                        'type': conv['type'],
                        'count': 0,
                        'users': 0
                    }
                conversion_events[event]['count'] += conv['count']
                conversion_events[event]['users'] += conv['users']

            total_conversions += data.get('conversions', {}).get('total', 0)

        # Convert to list
        events_list = []
        for event, data in conversion_events.items():
            events_list.append({
                'event': event,
                'type': data['type'],
                'count': data['count'],
                'users': data['users']
            })

        # Calculate conversion rate
        total_sessions = self._get_total_sessions(dates)
        conversion_rate = round((total_conversions / total_sessions * 100), 2) if total_sessions > 0 else 0

        return {
            'total': total_conversions,
            'conversion_rate': conversion_rate,
            'events': events_list
        }

    def _aggregate_traffic(self, dates: List[str]) -> Dict:
        """Aggregate traffic source data"""
        channels = {}

        for date in dates:
            filepath = self.base_dir / date / 'traffic_sources.json'
            if not filepath.exists():
                continue

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Aggregate channels
            for channel_data in data.get('channels', []):
                channel = channel_data['channel']
                if channel not in channels:
                    channels[channel] = {
                        'sessions': 0,
                        'conversions': 0
                    }
                channels[channel]['sessions'] += channel_data['sessions']
                channels[channel]['conversions'] += channel_data.get('conversions', 0)

        # Convert to list with conversion rates
        channels_list = []
        for channel, data in channels.items():
            sessions = data['sessions']
            conversions = data['conversions']
            conv_rate = round((conversions / sessions * 100), 2) if sessions > 0 else 0

            channels_list.append({
                'channel': channel,
                'sessions': sessions,
                'conversions': conversions,
                'conversion_rate': conv_rate
            })

        # Sort by sessions
        channels_list.sort(key=lambda x: x['sessions'], reverse=True)

        return {
            'channels': channels_list
        }

    def _aggregate_pages(self, dates: List[str]) -> Dict:
        """Aggregate page performance"""
        pages = {}

        for date in dates:
            filepath = self.base_dir / date / 'page_performance.json'
            if not filepath.exists():
                continue

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Handle both list format and dict format
            page_list = data if isinstance(data, list) else data.get('top_pages', [])

            # Aggregate pages
            for page_data in page_list:
                path = page_data['path']
                if path not in pages:
                    pages[path] = {
                        'views': 0,
                        'users': set()
                    }
                pages[path]['views'] += page_data['views']

        # Convert to list
        pages_list = []
        for path, data in pages.items():
            pages_list.append({
                'path': path,
                'views': data['views'],
                'users': data['views']  # Approximation
            })

        # Sort by views
        pages_list.sort(key=lambda x: x['views'], reverse=True)

        return {
            'top_pages': pages_list[:20]  # Top 20
        }

    def _get_total_sessions(self, dates: List[str]) -> int:
        """Get total sessions across dates"""
        total = 0
        for date in dates:
            filepath = self.base_dir / date / 'funnel_performance.json'
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    total += data.get('total_sessions', 0)
        return total
