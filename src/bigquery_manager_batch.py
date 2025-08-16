"""
BigQuery Manager Module (Batch Version)
Uses batch loading instead of streaming for free tier compatibility
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()


class BigQueryManager:
    """Manager for BigQuery operations using batch loading"""
    
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
        
        print(f"✅ BigQuery Manager (Batch) initialized for project: {self.project_id}")
    
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
    
    def _batch_load_json(self, table_name: str, rows: List[Dict]) -> bool:
        """
        Load data using batch loading (free tier compatible)
        
        Args:
            table_name: Name of the table
            rows: List of row dictionaries
        
        Returns:
            Success status
        """
        if not rows:
            return True
        
        table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
        
        # Write to temporary JSONL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for row in rows:
                f.write(json.dumps(row) + '\n')
            temp_file = f.name
        
        try:
            # Configure load job
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                autodetect=False  # Use existing schema
            )
            
            # Load from file
            with open(temp_file, 'rb') as f:
                load_job = self.client.load_table_from_file(
                    f, table_id, job_config=job_config
                )
            
            # Wait for job to complete
            load_job.result()
            
            print(f"✅ Batch loaded {len(rows)} rows to {table_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error batch loading to {table_name}: {e}")
            return False
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def insert_daily_metrics(self, metrics: Dict) -> bool:
        """Insert daily metrics using batch loading"""
        rows_to_insert = []
        for day_data in metrics.get('daily_metrics', []):
            # Convert date from YYYYMMDD to YYYY-MM-DD format
            date_str = day_data['date']
            if len(date_str) == 8:  # YYYYMMDD format
                date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                date_formatted = date_str
            
            row = {
                'date': date_formatted,
                'users': day_data['users'],
                'sessions': day_data['sessions'],
                'page_views': day_data['page_views'],
                'conversions': day_data.get('conversions', 0),
                'bounce_rate': day_data.get('bounce_rate', 0),
                'avg_session_duration': day_data.get('avg_session_duration', 0),
                'timestamp': datetime.now().isoformat()
            }
            rows_to_insert.append(row)
        
        return self._batch_load_json('daily_metrics', rows_to_insert)
    
    def insert_funnel_data(self, funnel_data: Dict) -> bool:
        """Insert funnel data using batch loading"""
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
        
        return self._batch_load_json('funnel_events', rows_to_insert)
    
    def insert_attribution_data(self, attribution_data: Dict) -> bool:
        """Insert attribution data using batch loading"""
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
        
        return self._batch_load_json('attribution_data', rows_to_insert)
    
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
    
    def log_alert(self, alert_type: str, severity: str, message: str, details: Dict = None) -> bool:
        """Log an alert using batch loading"""
        row = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'details': json.dumps(details) if details else '{}',
            'resolved': False
        }
        
        return self._batch_load_json('alerts', [row])


if __name__ == "__main__":
    # Test BigQuery Manager
    try:
        bq = BigQueryManager()
        
        print("\n🔧 Testing BigQuery Batch Operations...")
        print("-" * 50)
        
        # Test with sample data
        test_metrics = {
            'daily_metrics': [
                {
                    'date': datetime.now().date().isoformat(),
                    'users': 100,
                    'sessions': 150,
                    'page_views': 500,
                    'conversions': 5,
                    'bounce_rate': 0.45,
                    'avg_session_duration': 180.5
                }
            ]
        }
        
        success = bq.insert_daily_metrics(test_metrics)
        if success:
            print("✅ Batch loading test successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")