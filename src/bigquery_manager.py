"""
BigQuery Manager Module
Handles all BigQuery operations including dataset creation, data insertion, and queries
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import json

load_dotenv()


class BigQueryManager:
    """Manager for BigQuery operations"""
    
    def __init__(self):
        """Initialize BigQuery client"""
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found in environment")
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/bigquery']
        )
        
        self.client = bigquery.Client(
            credentials=credentials,
            project=os.getenv('GCP_PROJECT_ID', 'votegtr-analytics')
        )
        
        self.dataset_id = os.getenv('BIGQUERY_DATASET', 'votegtr_analytics')
        self.project_id = self.client.project
        
        print(f"✅ BigQuery Manager initialized for project: {self.project_id}")
    
    def create_dataset_if_not_exists(self) -> bool:
        """Create dataset if it doesn't exist"""
        dataset_full_id = f"{self.project_id}.{self.dataset_id}"
        
        try:
            self.client.get_dataset(dataset_full_id)
            print(f"📊 Dataset {self.dataset_id} already exists")
            return True
        except Exception:
            # Dataset doesn't exist, create it
            dataset = bigquery.Dataset(dataset_full_id)
            dataset.location = "US"
            dataset.description = "VOTEGTR Analytics Data"
            
            dataset = self.client.create_dataset(dataset, timeout=30)
            print(f"✅ Created dataset {self.dataset_id}")
            return True
    
    def create_tables(self) -> bool:
        """Create necessary tables if they don't exist"""
        tables = {
            'daily_metrics': [
                bigquery.SchemaField('date', 'DATE', mode='REQUIRED'),
                bigquery.SchemaField('users', 'INTEGER'),
                bigquery.SchemaField('sessions', 'INTEGER'),
                bigquery.SchemaField('page_views', 'INTEGER'),
                bigquery.SchemaField('conversions', 'INTEGER'),
                bigquery.SchemaField('bounce_rate', 'FLOAT'),
                bigquery.SchemaField('avg_session_duration', 'FLOAT'),
                bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
            ],
            'funnel_events': [
                bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('event_name', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('stage', 'STRING'),
                bigquery.SchemaField('user_count', 'INTEGER'),
                bigquery.SchemaField('event_count', 'INTEGER'),
                bigquery.SchemaField('conversion_rate', 'FLOAT'),
            ],
            'attribution_data': [
                bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('source', 'STRING'),
                bigquery.SchemaField('medium', 'STRING'),
                bigquery.SchemaField('campaign', 'STRING'),
                bigquery.SchemaField('channel', 'STRING'),
                bigquery.SchemaField('sessions', 'INTEGER'),
                bigquery.SchemaField('users', 'INTEGER'),
                bigquery.SchemaField('conversions', 'INTEGER'),
                bigquery.SchemaField('conversion_rate', 'FLOAT'),
            ],
            'purchases': [
                bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('session_id', 'STRING'),
                bigquery.SchemaField('customer_email', 'STRING'),
                bigquery.SchemaField('amount', 'FLOAT'),
                bigquery.SchemaField('currency', 'STRING'),
                bigquery.SchemaField('status', 'STRING'),
                bigquery.SchemaField('metadata', 'STRING'),
            ],
            'alerts': [
                bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('alert_type', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('severity', 'STRING'),
                bigquery.SchemaField('message', 'STRING'),
                bigquery.SchemaField('details', 'STRING'),
                bigquery.SchemaField('resolved', 'BOOLEAN'),
            ]
        }
        
        for table_name, schema in tables.items():
            table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            
            try:
                self.client.get_table(table_id)
                print(f"📋 Table {table_name} already exists")
            except Exception:
                # Table doesn't exist, create it
                table = bigquery.Table(table_id, schema=schema)
                table = self.client.create_table(table)
                print(f"✅ Created table {table_name}")
        
        return True
    
    def insert_daily_metrics(self, metrics: Dict) -> bool:
        """Insert daily metrics into BigQuery"""
        table_id = f"{self.project_id}.{self.dataset_id}.daily_metrics"
        
        rows_to_insert = []
        for day_data in metrics.get('daily_metrics', []):
            row = {
                'date': day_data['date'],
                'users': day_data['users'],
                'sessions': day_data['sessions'],
                'page_views': day_data['page_views'],
                'conversions': day_data.get('conversions', 0),
                'bounce_rate': day_data.get('bounce_rate', 0),
                'avg_session_duration': day_data.get('avg_session_duration', 0),
                'timestamp': datetime.now().isoformat()
            }
            rows_to_insert.append(row)
        
        if rows_to_insert:
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                print(f"❌ Error inserting daily metrics: {errors}")
                return False
            print(f"✅ Inserted {len(rows_to_insert)} daily metric rows")
        
        return True
    
    def insert_funnel_data(self, funnel_data: Dict) -> bool:
        """Insert funnel data into BigQuery"""
        table_id = f"{self.project_id}.{self.dataset_id}.funnel_events"
        
        rows_to_insert = []
        timestamp = datetime.now().isoformat()
        
        for stage in funnel_data.get('stages', []):
            row = {
                'timestamp': timestamp,
                'event_name': stage['event'],
                'stage': stage['stage'],
                'user_count': stage['users'],
                'event_count': stage['count'],
                'conversion_rate': stage['conversion_rate']
            }
            rows_to_insert.append(row)
        
        if rows_to_insert:
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                print(f"❌ Error inserting funnel data: {errors}")
                return False
            print(f"✅ Inserted {len(rows_to_insert)} funnel stage rows")
        
        return True
    
    def insert_attribution_data(self, attribution_data: Dict) -> bool:
        """Insert attribution data into BigQuery"""
        table_id = f"{self.project_id}.{self.dataset_id}.attribution_data"
        
        rows_to_insert = []
        timestamp = datetime.now().isoformat()
        
        for channel_data in attribution_data.get('channels', []):
            row = {
                'timestamp': timestamp,
                'source': channel_data['source'],
                'medium': channel_data['medium'],
                'campaign': channel_data['campaign'],
                'channel': channel_data['channel'],
                'sessions': channel_data['sessions'],
                'users': channel_data['users'],
                'conversions': channel_data['conversions'],
                'conversion_rate': channel_data['conversion_rate']
            }
            rows_to_insert.append(row)
        
        if rows_to_insert:
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            if errors:
                print(f"❌ Error inserting attribution data: {errors}")
                return False
            print(f"✅ Inserted {len(rows_to_insert)} attribution rows")
        
        return True
    
    def query_recent_metrics(self, days: int = 7) -> List[Dict]:
        """Query recent metrics from BigQuery"""
        query = f"""
        SELECT 
            date,
            users,
            sessions,
            page_views,
            conversions,
            bounce_rate,
            avg_session_duration
        FROM `{self.project_id}.{self.dataset_id}.daily_metrics`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY date DESC
        """
        
        query_job = self.client.query(query)
        results = []
        
        for row in query_job:
            results.append({
                'date': row.date.isoformat() if row.date else None,
                'users': row.users,
                'sessions': row.sessions,
                'page_views': row.page_views,
                'conversions': row.conversions,
                'bounce_rate': row.bounce_rate,
                'avg_session_duration': row.avg_session_duration
            })
        
        return results
    
    def query_funnel_performance(self, hours: int = 24) -> List[Dict]:
        """Query recent funnel performance"""
        query = f"""
        SELECT 
            event_name,
            stage,
            SUM(event_count) as total_events,
            AVG(conversion_rate) as avg_conversion_rate,
            MAX(timestamp) as last_updated
        FROM `{self.project_id}.{self.dataset_id}.funnel_events`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        GROUP BY event_name, stage
        ORDER BY avg_conversion_rate DESC
        """
        
        query_job = self.client.query(query)
        results = []
        
        for row in query_job:
            results.append({
                'event_name': row.event_name,
                'stage': row.stage,
                'total_events': row.total_events,
                'avg_conversion_rate': row.avg_conversion_rate,
                'last_updated': row.last_updated.isoformat() if row.last_updated else None
            })
        
        return results
    
    def get_attribution_summary(self) -> Dict:
        """Get attribution summary from BigQuery"""
        query = f"""
        WITH latest_data AS (
            SELECT 
                source,
                medium,
                SUM(sessions) as total_sessions,
                SUM(conversions) as total_conversions,
                AVG(conversion_rate) as avg_conversion_rate
            FROM `{self.project_id}.{self.dataset_id}.attribution_data`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            GROUP BY source, medium
        )
        SELECT 
            source,
            medium,
            total_sessions,
            total_conversions,
            avg_conversion_rate,
            ROUND(100.0 * total_sessions / SUM(total_sessions) OVER(), 2) as traffic_share
        FROM latest_data
        ORDER BY total_sessions DESC
        LIMIT 10
        """
        
        query_job = self.client.query(query)
        channels = []
        
        for row in query_job:
            channels.append({
                'source': row.source,
                'medium': row.medium,
                'sessions': row.total_sessions,
                'conversions': row.total_conversions,
                'conversion_rate': row.avg_conversion_rate,
                'traffic_share': row.traffic_share
            })
        
        return {
            'top_channels': channels,
            'total_channels': len(channels)
        }
    
    def log_alert(self, alert_type: str, severity: str, message: str, details: Dict = None) -> bool:
        """Log an alert to BigQuery"""
        table_id = f"{self.project_id}.{self.dataset_id}.alerts"
        
        row = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'details': json.dumps(details) if details else '{}',
            'resolved': False
        }
        
        errors = self.client.insert_rows_json(table_id, [row])
        if errors:
            print(f"❌ Error logging alert: {errors}")
            return False
        
        return True


if __name__ == "__main__":
    # Test BigQuery Manager
    try:
        bq = BigQueryManager()
        
        print("\n🔧 Setting up BigQuery...")
        print("-" * 50)
        
        # Create dataset and tables
        bq.create_dataset_if_not_exists()
        bq.create_tables()
        
        print("\n✅ BigQuery setup complete!")
        
        # Test query (will be empty initially)
        print("\n📊 Testing queries...")
        metrics = bq.query_recent_metrics(7)
        print(f"Found {len(metrics)} days of metrics in BigQuery")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")