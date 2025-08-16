"""
Optimized BigQuery Manager with Cost Controls
Implements partitioning, clustering, and cost optimization
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


class OptimizedBigQueryManager:
    """Optimized BigQuery manager with cost controls"""
    
    # Cost control constants
    MAX_BYTES_PER_QUERY = 100_000_000  # 100MB max per query
    MAX_QUERIES_PER_DAY = 1000
    MAX_DAILY_COST = 5.00  # $5 daily limit
    COST_PER_TB = 5.00  # $5 per TB processed
    
    def __init__(self):
        """Initialize BigQuery client with optimizations"""
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
        
        # Initialize cost tracking
        self.queries_today = 0
        self.bytes_processed_today = 0
        
        print(f"✅ Optimized BigQuery Manager initialized for project: {self.project_id}")
    
    def create_optimized_dataset(self) -> bool:
        """Create dataset with proper configuration"""
        dataset_full_id = f"{self.project_id}.{self.dataset_id}"
        
        try:
            dataset = self.client.get_dataset(dataset_full_id)
            print(f"📊 Dataset {self.dataset_id} already exists")
            
            # Update dataset to ensure proper settings
            dataset.default_table_expiration_ms = None  # No auto-expiration for main tables
            dataset.description = "VOTEGTR Analytics Data - Optimized"
            try:
                dataset = self.client.update_dataset(dataset, ["description", "default_table_expiration_ms"])
            except:
                pass  # Ignore update errors
            
        except Exception:
            # Dataset doesn't exist, create it
            dataset = bigquery.Dataset(dataset_full_id)
            dataset.location = "US"
            dataset.description = "VOTEGTR Analytics Data - Optimized"
            dataset = self.client.create_dataset(dataset, timeout=30)
            print(f"✅ Created optimized dataset {self.dataset_id}")
        
        return True
    
    def create_optimized_tables(self) -> bool:
        """Create optimized tables with partitioning and clustering"""
        
        # Define optimized table schemas
        tables_config = {
            'events_optimized': {
                'schema': [
                    bigquery.SchemaField('event_date', 'DATE', mode='REQUIRED'),
                    bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                    bigquery.SchemaField('event_name', 'STRING', mode='REQUIRED'),
                    bigquery.SchemaField('user_pseudo_id', 'STRING'),
                    bigquery.SchemaField('source', 'STRING'),
                    bigquery.SchemaField('medium', 'STRING'),
                    bigquery.SchemaField('campaign', 'STRING'),
                    bigquery.SchemaField('page_path', 'STRING'),
                    bigquery.SchemaField('event_count', 'INTEGER'),
                    bigquery.SchemaField('event_value', 'FLOAT'),
                ],
                'partition_field': 'event_date',
                'clustering_fields': ['event_name', 'source', 'medium'],
                'description': 'Optimized events table with partitioning and clustering'
            },
            'daily_metrics_optimized': {
                'schema': [
                    bigquery.SchemaField('date', 'DATE', mode='REQUIRED'),
                    bigquery.SchemaField('source', 'STRING'),
                    bigquery.SchemaField('medium', 'STRING'),
                    bigquery.SchemaField('campaign', 'STRING'),
                    bigquery.SchemaField('users', 'INTEGER'),
                    bigquery.SchemaField('sessions', 'INTEGER'),
                    bigquery.SchemaField('page_views', 'INTEGER'),
                    bigquery.SchemaField('conversions', 'INTEGER'),
                    bigquery.SchemaField('bounce_rate', 'FLOAT'),
                    bigquery.SchemaField('avg_session_duration', 'FLOAT'),
                    bigquery.SchemaField('revenue', 'FLOAT'),
                    bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                ],
                'partition_field': 'date',
                'clustering_fields': ['source', 'medium', 'campaign'],
                'description': 'Daily aggregated metrics - partitioned and clustered'
            },
            'cost_tracking': {
                'schema': [
                    bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                    bigquery.SchemaField('date', 'DATE', mode='REQUIRED'),
                    bigquery.SchemaField('query_id', 'STRING'),
                    bigquery.SchemaField('query_type', 'STRING'),
                    bigquery.SchemaField('bytes_processed', 'INTEGER'),
                    bigquery.SchemaField('bytes_billed', 'INTEGER'),
                    bigquery.SchemaField('estimated_cost', 'FLOAT'),
                    bigquery.SchemaField('query_text', 'STRING'),
                    bigquery.SchemaField('user', 'STRING'),
                    bigquery.SchemaField('duration_ms', 'INTEGER'),
                ],
                'partition_field': 'date',
                'clustering_fields': ['query_type', 'user'],
                'description': 'Query cost tracking for monitoring'
            },
            'hourly_cache': {
                'schema': [
                    bigquery.SchemaField('cache_hour', 'DATETIME', mode='REQUIRED'),
                    bigquery.SchemaField('metric_type', 'STRING'),
                    bigquery.SchemaField('metric_value', 'FLOAT'),
                    bigquery.SchemaField('dimensions', 'JSON'),
                    bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED'),
                ],
                'partition_field': 'cache_hour',
                'clustering_fields': ['metric_type'],
                'description': 'Hourly cache for frequent queries',
                'expiration_days': 7  # Auto-delete after 7 days
            }
        }
        
        for table_name, config in tables_config.items():
            table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
            
            try:
                table = self.client.get_table(table_id)
                print(f"📋 Table {table_name} already exists")
                
                # Check if we need to update the table
                if hasattr(table, 'time_partitioning') and not table.time_partitioning:
                    print(f"⚠️  Table {table_name} exists but is not optimized. Consider recreating it.")
                    
            except Exception:
                # Table doesn't exist, create it with optimizations
                table = bigquery.Table(table_id, schema=config['schema'])
                
                # Set partitioning
                if config.get('partition_field'):
                    table.time_partitioning = bigquery.TimePartitioning(
                        type_=bigquery.TimePartitioningType.DAY,
                        field=config['partition_field']
                    )
                
                # Set clustering
                if config.get('clustering_fields'):
                    table.clustering_fields = config['clustering_fields']
                
                # Set description
                table.description = config.get('description', '')
                
                # Set expiration if specified
                if config.get('expiration_days'):
                    table.expires = datetime.now() + timedelta(days=config['expiration_days'])
                
                table = self.client.create_table(table)
                print(f"✅ Created optimized table {table_name}")
                print(f"   Partitioned by: {config.get('partition_field')}")
                print(f"   Clustered by: {config.get('clustering_fields')}")
        
        return True
    
    def create_materialized_views(self) -> bool:
        """Create materialized views for common queries"""
        
        views = {
            'dashboard_summary': """
                CREATE MATERIALIZED VIEW IF NOT EXISTS `{project}.{dataset}.dashboard_summary`
                PARTITION BY date
                CLUSTER BY source, medium
                AS
                SELECT 
                    date,
                    source,
                    medium,
                    SUM(users) as total_users,
                    SUM(sessions) as total_sessions,
                    SUM(page_views) as total_page_views,
                    SUM(conversions) as total_conversions,
                    AVG(bounce_rate) as avg_bounce_rate,
                    AVG(avg_session_duration) as avg_session_duration,
                    SUM(revenue) as total_revenue
                FROM `{project}.{dataset}.daily_metrics_optimized`
                WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
                GROUP BY date, source, medium
            """,
            'weekly_funnel': """
                CREATE MATERIALIZED VIEW IF NOT EXISTS `{project}.{dataset}.weekly_funnel`
                PARTITION BY week_start
                AS
                SELECT 
                    DATE_TRUNC(event_date, WEEK) as week_start,
                    event_name,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_pseudo_id) as unique_users
                FROM `{project}.{dataset}.events_optimized`
                WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                GROUP BY week_start, event_name
            """
        }
        
        for view_name, query_template in views.items():
            try:
                query = query_template.format(
                    project=self.project_id,
                    dataset=self.dataset_id
                )
                
                # Note: BigQuery materialized views have limitations in free tier
                # For now, we'll create regular views that can be manually refreshed
                view_query = query.replace("CREATE MATERIALIZED VIEW", "CREATE OR REPLACE VIEW")
                
                self.client.query(view_query).result()
                print(f"✅ Created view: {view_name}")
                
            except Exception as e:
                print(f"⚠️  Could not create view {view_name}: {e}")
        
        return True
    
    def estimate_query_cost(self, query: str) -> Dict[str, Any]:
        """
        Estimate query cost before execution
        
        Args:
            query: SQL query to estimate
            
        Returns:
            Dict with cost estimation details
        """
        try:
            # Perform dry run to get bytes processed
            job_config = bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False
            )
            
            query_job = self.client.query(query, job_config=job_config)
            
            bytes_processed = query_job.total_bytes_processed
            estimated_cost = (bytes_processed / 1_000_000_000_000) * self.COST_PER_TB
            
            return {
                'bytes_processed': bytes_processed,
                'estimated_cost': estimated_cost,
                'cost_warning': estimated_cost > 0.10,
                'within_limit': bytes_processed <= self.MAX_BYTES_PER_QUERY
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'bytes_processed': 0,
                'estimated_cost': 0,
                'within_limit': False
            }
    
    def execute_query_with_cost_control(self, query: str, query_type: str = 'general') -> Any:
        """
        Execute query with cost controls and tracking
        
        Args:
            query: SQL query to execute
            query_type: Type of query for tracking
            
        Returns:
            Query results or raises exception if limits exceeded
        """
        # Check daily limits
        if self.queries_today >= self.MAX_QUERIES_PER_DAY:
            raise Exception(f"Daily query limit ({self.MAX_QUERIES_PER_DAY}) exceeded")
        
        # Estimate cost first
        cost_estimate = self.estimate_query_cost(query)
        
        if not cost_estimate['within_limit']:
            raise Exception(f"Query exceeds byte limit: {cost_estimate['bytes_processed']} bytes")
        
        if cost_estimate.get('cost_warning'):
            print(f"⚠️  High cost query warning: ${cost_estimate['estimated_cost']:.4f}")
        
        # Add optimization hints to query
        optimized_query = self._add_query_optimizations(query)
        
        # Configure job with limits
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=self.MAX_BYTES_PER_QUERY,
            use_query_cache=True,
            priority=bigquery.QueryPriority.INTERACTIVE
        )
        
        start_time = datetime.now()
        
        try:
            # Execute query
            query_job = self.client.query(optimized_query, job_config=job_config)
            results = query_job.result()
            
            # Track costs
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._track_query_cost(
                query_job=query_job,
                query_type=query_type,
                query_text=optimized_query[:500],  # First 500 chars
                duration_ms=duration_ms
            )
            
            # Update daily counters
            self.queries_today += 1
            self.bytes_processed_today += query_job.total_bytes_billed or 0
            
            return results
            
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            raise
    
    def _add_query_optimizations(self, query: str) -> str:
        """Add automatic optimizations to queries"""
        
        # Add partition filter if missing
        if 'WHERE' in query.upper() and 'DATE' not in query.upper():
            # Query has WHERE but no date filter - risky!
            print("⚠️  Query missing date filter - adding 30 day limit")
            query = query.replace('WHERE', 
                'WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND')
        
        # Add LIMIT if missing (for SELECT queries without aggregation)
        if 'SELECT' in query.upper() and 'LIMIT' not in query.upper() and 'GROUP BY' not in query.upper():
            query += ' LIMIT 10000'
        
        return query
    
    def _track_query_cost(self, query_job, query_type: str, query_text: str, duration_ms: int):
        """Track query costs in BigQuery"""
        
        bytes_billed = query_job.total_bytes_billed or 0
        bytes_processed = query_job.total_bytes_processed or 0
        estimated_cost = (bytes_billed / 1_000_000_000_000) * self.COST_PER_TB
        
        # Log to cost tracking table
        row = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().date().isoformat(),
            'query_id': query_job.job_id,
            'query_type': query_type,
            'bytes_processed': bytes_processed,
            'bytes_billed': bytes_billed,
            'estimated_cost': estimated_cost,
            'query_text': query_text,
            'user': 'system',
            'duration_ms': duration_ms
        }
        
        # Use batch loading to avoid streaming insert costs
        table_id = f"{self.project_id}.{self.dataset_id}.cost_tracking"
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                f.write(json.dumps(row) + '\n')
                temp_file = f.name
            
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND
            )
            
            with open(temp_file, 'rb') as f:
                load_job = self.client.load_table_from_file(f, table_id, job_config=job_config)
            
            load_job.result()  # Wait for completion
            
        except Exception as e:
            print(f"⚠️  Could not track query cost: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def get_daily_cost_summary(self) -> Dict[str, Any]:
        """Get today's cost summary"""
        
        query = f"""
        SELECT 
            COUNT(*) as query_count,
            SUM(bytes_processed) as total_bytes,
            SUM(bytes_billed) as total_billed,
            SUM(estimated_cost) as total_cost,
            AVG(duration_ms) as avg_duration_ms
        FROM `{self.project_id}.{self.dataset_id}.cost_tracking`
        WHERE date = CURRENT_DATE()
        """
        
        try:
            results = list(self.execute_query_with_cost_control(query, 'cost_monitoring'))
            
            if results:
                row = results[0]
                return {
                    'date': datetime.now().date().isoformat(),
                    'query_count': row.query_count or 0,
                    'total_bytes': row.total_bytes or 0,
                    'total_cost': row.total_cost or 0,
                    'avg_duration_ms': row.avg_duration_ms or 0,
                    'budget_remaining': self.MAX_DAILY_COST - (row.total_cost or 0),
                    'budget_percentage': ((row.total_cost or 0) / self.MAX_DAILY_COST) * 100
                }
        except:
            pass
        
        return {
            'date': datetime.now().date().isoformat(),
            'query_count': 0,
            'total_bytes': 0,
            'total_cost': 0,
            'budget_remaining': self.MAX_DAILY_COST,
            'budget_percentage': 0
        }
    
    def optimize_existing_table(self, source_table: str, target_table: str, 
                               partition_field: str, clustering_fields: List[str]) -> bool:
        """
        Migrate existing table to optimized version
        
        Args:
            source_table: Name of existing table
            target_table: Name of new optimized table
            partition_field: Field to partition by
            clustering_fields: Fields to cluster by
        """
        
        query = f"""
        CREATE OR REPLACE TABLE `{self.project_id}.{self.dataset_id}.{target_table}`
        PARTITION BY {partition_field}
        CLUSTER BY {', '.join(clustering_fields)}
        AS
        SELECT * FROM `{self.project_id}.{self.dataset_id}.{source_table}`
        """
        
        try:
            self.execute_query_with_cost_control(query, 'table_optimization')
            print(f"✅ Optimized table created: {target_table}")
            return True
        except Exception as e:
            print(f"❌ Failed to optimize table: {e}")
            return False


if __name__ == "__main__":
    # Test optimized BigQuery manager
    try:
        bq = OptimizedBigQueryManager()
        
        print("\n🔧 Setting up Optimized BigQuery...")
        print("-" * 50)
        
        # Create optimized dataset and tables
        bq.create_optimized_dataset()
        bq.create_optimized_tables()
        bq.create_materialized_views()
        
        # Check daily costs
        print("\n💰 Daily Cost Summary:")
        cost_summary = bq.get_daily_cost_summary()
        print(f"   Queries today: {cost_summary['query_count']}")
        print(f"   Total cost: ${cost_summary['total_cost']:.4f}")
        print(f"   Budget used: {cost_summary['budget_percentage']:.1f}%")
        print(f"   Budget remaining: ${cost_summary['budget_remaining']:.2f}")
        
        print("\n✅ Optimized BigQuery setup complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")