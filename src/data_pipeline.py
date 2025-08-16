"""
Data Pipeline Module
Orchestrates data flow from GA4 to BigQuery
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from dotenv import load_dotenv

from ga4_client import GA4Client
from bigquery_manager_batch import BigQueryManager

load_dotenv()


class DataPipeline:
    """Manages data flow from GA4 to BigQuery"""
    
    def __init__(self):
        """Initialize pipeline components"""
        self.ga4 = GA4Client()
        self.bq = BigQueryManager()
        print("✅ Data Pipeline initialized")
    
    def sync_daily_metrics(self, days: int = 7) -> bool:
        """
        Sync daily metrics from GA4 to BigQuery
        
        Args:
            days: Number of days to sync
        
        Returns:
            Success status
        """
        print(f"\n📊 Syncing {days} days of metrics...")
        
        try:
            # Get metrics from GA4
            metrics = self.ga4.get_daily_metrics(days)
            
            # Insert into BigQuery
            success = self.bq.insert_daily_metrics(metrics)
            
            if success:
                print(f"✅ Synced {len(metrics['daily_metrics'])} days of data")
                print(f"   Total sessions: {metrics['totals']['total_sessions']}")
                print(f"   Total conversions: {metrics['totals']['total_conversions']}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error syncing daily metrics: {e}")
            self.bq.log_alert(
                alert_type='data_sync_error',
                severity='high',
                message=f'Failed to sync daily metrics: {str(e)}',
                details={'days': days}
            )
            return False
    
    def sync_funnel_data(self, date_range: str = '7daysAgo') -> bool:
        """
        Sync funnel data from GA4 to BigQuery
        
        Args:
            date_range: Start date for funnel data
        
        Returns:
            Success status
        """
        print(f"\n🔄 Syncing funnel data...")
        
        try:
            # Get funnel metrics from GA4
            funnel_data = self.ga4.get_funnel_metrics(date_range, 'today')
            
            # Insert into BigQuery
            success = self.bq.insert_funnel_data(funnel_data)
            
            if success:
                print(f"✅ Synced {len(funnel_data['stages'])} funnel stages")
                for stage in funnel_data['stages'][:3]:
                    print(f"   {stage['stage']}: {stage['count']} events")
            
            return success
            
        except Exception as e:
            print(f"❌ Error syncing funnel data: {e}")
            self.bq.log_alert(
                alert_type='data_sync_error',
                severity='high',
                message=f'Failed to sync funnel data: {str(e)}',
                details={'date_range': date_range}
            )
            return False
    
    def sync_attribution_data(self, date_range: str = '7daysAgo') -> bool:
        """
        Sync attribution data from GA4 to BigQuery
        
        Args:
            date_range: Start date for attribution data
        
        Returns:
            Success status
        """
        print(f"\n🎯 Syncing attribution data...")
        
        try:
            # Get attribution data from GA4
            attribution_data = self.ga4.get_attribution_data(date_range, 'today')
            
            # Insert into BigQuery
            success = self.bq.insert_attribution_data(attribution_data)
            
            if success:
                print(f"✅ Synced {len(attribution_data['channels'])} channels")
                print(f"   UTM coverage: {attribution_data['utm_coverage']:.1f}%")
                print(f"   Total conversions: {attribution_data['total_conversions']}")
                
                # Check UTM coverage and alert if low
                if attribution_data['utm_coverage'] < 75:
                    self.bq.log_alert(
                        alert_type='low_utm_coverage',
                        severity='medium',
                        message=f'UTM coverage is {attribution_data["utm_coverage"]:.1f}%',
                        details={'coverage': attribution_data['utm_coverage']}
                    )
            
            return success
            
        except Exception as e:
            print(f"❌ Error syncing attribution data: {e}")
            self.bq.log_alert(
                alert_type='data_sync_error',
                severity='high',
                message=f'Failed to sync attribution data: {str(e)}',
                details={'date_range': date_range}
            )
            return False
    
    def run_full_sync(self) -> Dict[str, bool]:
        """
        Run full data sync from GA4 to BigQuery
        
        Returns:
            Dictionary of sync results
        """
        print("\n" + "="*50)
        print("🚀 Starting Full Data Sync")
        print("="*50)
        
        start_time = time.time()
        results = {}
        
        # Sync all data types
        results['daily_metrics'] = self.sync_daily_metrics(7)
        results['funnel_data'] = self.sync_funnel_data('7daysAgo')
        results['attribution_data'] = self.sync_attribution_data('7daysAgo')
        
        # Calculate success rate
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        success_rate = (success_count / total_count) * 100
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "="*50)
        print("📋 Sync Summary")
        print("="*50)
        print(f"✅ Successful: {success_count}/{total_count}")
        print(f"📊 Success Rate: {success_rate:.0f}%")
        print(f"⏱️  Time Elapsed: {elapsed_time:.2f} seconds")
        
        # Log overall sync status
        if success_rate < 100:
            self.bq.log_alert(
                alert_type='partial_sync_failure',
                severity='medium',
                message=f'Data sync partially failed: {success_rate:.0f}% success rate',
                details=results
            )
        
        return results
    
    def check_data_health(self) -> Dict[str, Any]:
        """
        Check overall data health and quality
        
        Returns:
            Health status dictionary
        """
        print("\n🏥 Checking Data Health...")
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'ga4_status': 'unknown',
            'bigquery_status': 'unknown',
            'issues': []
        }
        
        # Check GA4 data quality
        try:
            ga4_health = self.ga4.check_data_quality()
            health_status['ga4_status'] = ga4_health['status']
            
            if ga4_health['missing_events']:
                health_status['issues'].append(f"Missing GA4 events: {', '.join(ga4_health['missing_events'])}")
            
            if ga4_health['attribution_rate'] < 75:
                health_status['issues'].append(f"Low attribution rate: {ga4_health['attribution_rate']:.1f}%")
            
            print(f"  GA4 Status: {ga4_health['status']}")
            print(f"  Attribution Rate: {ga4_health['attribution_rate']:.1f}%")
            
        except Exception as e:
            health_status['ga4_status'] = 'error'
            health_status['issues'].append(f"GA4 health check failed: {str(e)}")
        
        # Check BigQuery data freshness
        try:
            recent_metrics = self.bq.query_recent_metrics(1)
            if recent_metrics:
                health_status['bigquery_status'] = 'healthy'
                print(f"  BigQuery Status: healthy")
            else:
                health_status['bigquery_status'] = 'stale'
                health_status['issues'].append("No recent data in BigQuery")
                print(f"  BigQuery Status: stale (no recent data)")
                
        except Exception as e:
            health_status['bigquery_status'] = 'error'
            health_status['issues'].append(f"BigQuery health check failed: {str(e)}")
        
        # Overall health determination
        if not health_status['issues']:
            health_status['overall'] = 'healthy'
            print("\n✅ Overall Data Health: HEALTHY")
        elif len(health_status['issues']) == 1:
            health_status['overall'] = 'warning'
            print(f"\n⚠️  Overall Data Health: WARNING")
            print(f"   Issues: {health_status['issues'][0]}")
        else:
            health_status['overall'] = 'critical'
            print(f"\n❌ Overall Data Health: CRITICAL")
            for issue in health_status['issues']:
                print(f"   - {issue}")
        
        return health_status
    
    def run_hourly_sync(self) -> bool:
        """
        Run hourly sync (lighter than full sync)
        
        Returns:
            Success status
        """
        print(f"\n⏰ Running hourly sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Sync today's metrics only
            metrics = self.ga4.get_daily_metrics(1)
            self.bq.insert_daily_metrics(metrics)
            
            # Sync recent funnel data
            funnel_data = self.ga4.get_funnel_metrics('today', 'today')
            self.bq.insert_funnel_data(funnel_data)
            
            print("✅ Hourly sync complete")
            return True
            
        except Exception as e:
            print(f"❌ Hourly sync failed: {e}")
            return False


if __name__ == "__main__":
    # Test the pipeline
    try:
        pipeline = DataPipeline()
        
        # Run full sync
        pipeline.run_full_sync()
        
        # Check data health
        pipeline.check_data_health()
        
    except Exception as e:
        print(f"\n❌ Pipeline Error: {e}")