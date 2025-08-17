"""
Dashboard Builder Module
Prepares data and configurations for Looker Studio dashboards
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()


class DashboardBuilder:
    """Creates and manages dashboard data views in BigQuery for Looker Studio"""
    
    def __init__(self):
        """Initialize dashboard builder"""
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found")
        
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
        
        print("✅ Dashboard Builder initialized")
    
    def create_dashboard_views(self) -> bool:
        """
        Create optimized views in BigQuery for Looker Studio dashboards
        """
        views = {
            'executive_summary_view': """
                CREATE OR REPLACE VIEW `{project}.{dataset}.executive_summary_view` AS
                WITH daily_stats AS (
                    SELECT 
                        date,
                        SUM(users) as total_users,
                        SUM(sessions) as total_sessions,
                        SUM(page_views) as total_page_views,
                        SUM(conversions) as total_conversions,
                        AVG(bounce_rate) as avg_bounce_rate,
                        AVG(avg_session_duration) as avg_session_duration
                    FROM `{project}.{dataset}.daily_metrics_optimized`
                    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                    GROUP BY date
                ),
                week_over_week AS (
                    SELECT 
                        DATE_TRUNC(date, WEEK) as week,
                        SUM(total_sessions) as weekly_sessions,
                        LAG(SUM(total_sessions)) OVER (ORDER BY DATE_TRUNC(date, WEEK)) as prev_week_sessions
                    FROM daily_stats
                    GROUP BY week
                )
                SELECT 
                    d.*,
                    w.weekly_sessions,
                    w.prev_week_sessions,
                    SAFE_DIVIDE((w.weekly_sessions - w.prev_week_sessions), w.prev_week_sessions) * 100 as wow_change
                FROM daily_stats d
                LEFT JOIN week_over_week w ON DATE_TRUNC(d.date, WEEK) = w.week
                ORDER BY date DESC
            """,
            
            'funnel_analysis_view': """
                CREATE OR REPLACE VIEW `{project}.{dataset}.funnel_analysis_view` AS
                SELECT 
                    timestamp,
                    event_name,
                    stage,
                    SUM(event_count) as total_events,
                    SUM(user_count) as total_users,
                    AVG(conversion_rate) as avg_conversion_rate,
                    MAX(conversion_rate) as max_conversion_rate,
                    MIN(conversion_rate) as min_conversion_rate
                FROM `{project}.{dataset}.funnel_events`
                WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                GROUP BY timestamp, event_name, stage
                ORDER BY avg_conversion_rate DESC
            """,
            
            'attribution_dashboard_view': """
                CREATE OR REPLACE VIEW `{project}.{dataset}.attribution_dashboard_view` AS
                WITH channel_stats AS (
                    SELECT 
                        source,
                        medium,
                        CONCAT(source, ' / ', medium) as channel,
                        campaign,
                        SUM(sessions) as total_sessions,
                        SUM(users) as total_users,
                        SUM(conversions) as total_conversions,
                        SAFE_DIVIDE(SUM(conversions), SUM(sessions)) * 100 as conversion_rate
                    FROM `{project}.{dataset}.attribution_data`
                    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                    GROUP BY source, medium, channel, campaign
                ),
                utm_coverage AS (
                    SELECT 
                        COUNTIF(source NOT IN ('(direct)', '(not set)')) as attributed_sessions,
                        COUNT(*) as total_sessions,
                        SAFE_DIVIDE(COUNTIF(source NOT IN ('(direct)', '(not set)')), COUNT(*)) * 100 as utm_coverage_rate
                    FROM `{project}.{dataset}.attribution_data`
                    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
                )
                SELECT 
                    c.*,
                    u.utm_coverage_rate,
                    RANK() OVER (ORDER BY c.total_sessions DESC) as session_rank,
                    RANK() OVER (ORDER BY c.conversion_rate DESC) as conversion_rank
                FROM channel_stats c
                CROSS JOIN utm_coverage u
            """,
            
            'cost_monitoring_view': """
                CREATE OR REPLACE VIEW `{project}.{dataset}.cost_monitoring_view` AS
                WITH daily_costs AS (
                    SELECT 
                        date,
                        COUNT(*) as query_count,
                        SUM(bytes_processed) / 1000000000000 as tb_processed,
                        SUM(estimated_cost) as total_cost,
                        AVG(duration_ms) as avg_query_time,
                        MAX(estimated_cost) as max_query_cost
                    FROM `{project}.{dataset}.cost_tracking`
                    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                    GROUP BY date
                ),
                budget_status AS (
                    SELECT 
                        CURRENT_DATE() as today,
                        COALESCE(SUM(total_cost), 0) as today_cost,
                        5.00 as daily_budget,
                        SAFE_DIVIDE(COALESCE(SUM(total_cost), 0), 5.00) * 100 as budget_used_pct,
                        5.00 - COALESCE(SUM(total_cost), 0) as budget_remaining
                    FROM daily_costs
                    WHERE date = CURRENT_DATE()
                )
                SELECT 
                    d.*,
                    b.today_cost,
                    b.daily_budget,
                    b.budget_used_pct,
                    b.budget_remaining,
                    CASE 
                        WHEN b.budget_used_pct >= 90 THEN 'CRITICAL'
                        WHEN b.budget_used_pct >= 70 THEN 'WARNING'
                        ELSE 'HEALTHY'
                    END as budget_status
                FROM daily_costs d
                CROSS JOIN budget_status b
                ORDER BY date DESC
            """,
            
            'real_time_metrics_view': """
                CREATE OR REPLACE VIEW `{project}.{dataset}.real_time_metrics_view` AS
                SELECT 
                    CURRENT_TIMESTAMP() as snapshot_time,
                    CURRENT_DATE() as date,
                    EXTRACT(HOUR FROM CURRENT_TIMESTAMP()) as hour,
                    (
                        SELECT COUNT(DISTINCT user_pseudo_id)
                        FROM `{project}.{dataset}.events_optimized`
                        WHERE event_date = CURRENT_DATE()
                        AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
                    ) as active_users_5min,
                    (
                        SELECT COUNT(*)
                        FROM `{project}.{dataset}.events_optimized`
                        WHERE event_date = CURRENT_DATE()
                    ) as events_today,
                    (
                        SELECT COUNT(*)
                        FROM `{project}.{dataset}.events_optimized`
                        WHERE event_date = CURRENT_DATE()
                        AND event_name = 'page_view'
                    ) as pageviews_today,
                    (
                        SELECT COUNT(*)
                        FROM `{project}.{dataset}.events_optimized`
                        WHERE event_date = CURRENT_DATE()
                        AND event_name IN ('form_submit', 'purchase_completed')
                    ) as conversions_today
            """,
            
            'top_content_view': """
                CREATE OR REPLACE VIEW `{project}.{dataset}.top_content_view` AS
                SELECT 
                    page_path,
                    COUNT(*) as pageviews,
                    COUNT(DISTINCT user_pseudo_id) as unique_users,
                    AVG(CAST(event_value AS FLOAT64)) as avg_time_on_page,
                    SUM(CASE WHEN event_name = 'form_submit' THEN 1 ELSE 0 END) as conversions_from_page
                FROM `{project}.{dataset}.events_optimized`
                WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
                    AND page_path IS NOT NULL
                GROUP BY page_path
                ORDER BY pageviews DESC
                LIMIT 100
            """
        }
        
        created_views = []
        failed_views = []
        
        for view_name, query_template in views.items():
            try:
                query = query_template.format(
                    project=self.project_id,
                    dataset=self.dataset_id
                )
                
                # Execute query to create view
                query_job = self.client.query(query)
                query_job.result()  # Wait for completion
                
                print(f"✅ Created view: {view_name}")
                created_views.append(view_name)
                
            except Exception as e:
                print(f"⚠️  Could not create view {view_name}: {e}")
                failed_views.append(view_name)
        
        # Summary
        print(f"\n📊 Dashboard Views Summary:")
        print(f"   Created: {len(created_views)} views")
        print(f"   Failed: {len(failed_views)} views")
        
        return len(failed_views) == 0
    
    def create_looker_studio_config(self) -> Dict[str, Any]:
        """
        Generate Looker Studio configuration for easy dashboard creation
        """
        config = {
            "dashboard_name": "VOTEGTR Analytics Dashboard",
            "data_sources": [
                {
                    "name": "Executive Summary",
                    "type": "BigQuery",
                    "project": self.project_id,
                    "dataset": self.dataset_id,
                    "table": "executive_summary_view"
                },
                {
                    "name": "Funnel Analysis",
                    "type": "BigQuery",
                    "project": self.project_id,
                    "dataset": self.dataset_id,
                    "table": "funnel_analysis_view"
                },
                {
                    "name": "Attribution",
                    "type": "BigQuery",
                    "project": self.project_id,
                    "dataset": self.dataset_id,
                    "table": "attribution_dashboard_view"
                },
                {
                    "name": "Cost Monitoring",
                    "type": "BigQuery",
                    "project": self.project_id,
                    "dataset": self.dataset_id,
                    "table": "cost_monitoring_view"
                }
            ],
            "pages": [
                {
                    "name": "Executive Summary",
                    "widgets": [
                        {
                            "type": "scorecard",
                            "title": "Total Sessions",
                            "metric": "total_sessions",
                            "comparison": "previous_period"
                        },
                        {
                            "type": "scorecard",
                            "title": "Conversion Rate",
                            "metric": "conversion_rate",
                            "format": "percent"
                        },
                        {
                            "type": "time_series",
                            "title": "Daily Traffic",
                            "dimension": "date",
                            "metrics": ["total_users", "total_sessions"]
                        },
                        {
                            "type": "pie_chart",
                            "title": "Traffic Sources",
                            "dimension": "channel",
                            "metric": "total_sessions"
                        }
                    ]
                },
                {
                    "name": "Funnel Analysis",
                    "widgets": [
                        {
                            "type": "funnel",
                            "title": "Conversion Funnel",
                            "dimension": "stage",
                            "metric": "total_events"
                        },
                        {
                            "type": "table",
                            "title": "Stage Details",
                            "dimensions": ["stage", "event_name"],
                            "metrics": ["total_events", "avg_conversion_rate"]
                        }
                    ]
                },
                {
                    "name": "Attribution",
                    "widgets": [
                        {
                            "type": "scorecard",
                            "title": "UTM Coverage",
                            "metric": "utm_coverage_rate",
                            "format": "percent"
                        },
                        {
                            "type": "table",
                            "title": "Channel Performance",
                            "dimensions": ["channel", "campaign"],
                            "metrics": ["total_sessions", "total_conversions", "conversion_rate"]
                        }
                    ]
                },
                {
                    "name": "Cost Monitoring",
                    "widgets": [
                        {
                            "type": "scorecard",
                            "title": "Today's Cost",
                            "metric": "today_cost",
                            "format": "currency"
                        },
                        {
                            "type": "gauge",
                            "title": "Budget Usage",
                            "metric": "budget_used_pct",
                            "max": 100,
                            "thresholds": [70, 90]
                        },
                        {
                            "type": "time_series",
                            "title": "Daily Costs",
                            "dimension": "date",
                            "metric": "total_cost"
                        }
                    ]
                }
            ],
            "filters": [
                {
                    "type": "date_range",
                    "default": "last_28_days"
                }
            ],
            "theme": {
                "primary_color": "#667eea",
                "secondary_color": "#764ba2",
                "font": "Roboto"
            }
        }
        
        # Save configuration
        config_path = "dashboards/looker_studio_config.json"
        os.makedirs("dashboards", exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📁 Looker Studio configuration saved to: {config_path}")
        
        return config
    
    def generate_dashboard_url(self) -> str:
        """
        Generate URL to create new Looker Studio report with BigQuery connection
        """
        base_url = "https://lookerstudio.google.com/c/create"
        
        # Parameters for quick setup
        params = {
            "project": self.project_id,
            "dataset": self.dataset_id,
            "table": "executive_summary_view"
        }
        
        # Create shareable link
        url = f"{base_url}?connector=bigquery&project={params['project']}&dataset={params['dataset']}"
        
        print(f"\n🔗 Quick Dashboard Setup URL:")
        print(f"   {url}")
        print(f"\n📝 Instructions:")
        print(f"   1. Click the link above")
        print(f"   2. Select 'executive_summary_view' as your first table")
        print(f"   3. Use the configuration in dashboards/looker_studio_config.json")
        
        return url


if __name__ == "__main__":
    # Test dashboard builder
    try:
        builder = DashboardBuilder()
        
        print("\n📊 Creating Dashboard Views in BigQuery...")
        print("-" * 50)
        
        # Create optimized views
        success = builder.create_dashboard_views()
        
        if success:
            print("\n✅ All dashboard views created successfully!")
            
            # Generate configuration
            config = builder.create_looker_studio_config()
            
            # Generate setup URL
            url = builder.generate_dashboard_url()
            
            print("\n📋 Next Steps:")
            print("   1. Open the URL above in your browser")
            print("   2. Connect to the BigQuery views")
            print("   3. Use the config file to set up widgets")
            
        else:
            print("\n⚠️  Some views failed to create - check table structures")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")