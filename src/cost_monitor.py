"""
Cost Monitoring Module
Tracks and controls Google Cloud costs
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class CostStatus(Enum):
    """Cost status indicators"""
    HEALTHY = "healthy"  # Under 50% of budget
    WARNING = "warning"  # 50-80% of budget
    CRITICAL = "critical"  # 80-95% of budget
    EXCEEDED = "exceeded"  # Over budget


@dataclass
class CostThresholds:
    """Cost thresholds and limits"""
    hourly_limit: float = 0.25  # $0.25/hour
    daily_limit: float = 5.00  # $5/day
    monthly_limit: float = 150.00  # $150/month
    
    query_cost_warning: float = 0.10  # Warn if single query > $0.10
    query_cost_limit: float = 1.00  # Block if single query > $1.00
    
    bytes_per_query_limit: int = 100_000_000  # 100MB
    queries_per_hour_limit: int = 100
    queries_per_day_limit: int = 1000


class CostMonitor:
    """Monitors and controls BigQuery costs"""
    
    def __init__(self, bigquery_manager=None):
        """
        Initialize cost monitor
        
        Args:
            bigquery_manager: Optional BigQuery manager instance
        """
        self.thresholds = CostThresholds()
        self.bq = bigquery_manager
        
        # Track current usage
        self.current_hour_queries = 0
        self.current_day_queries = 0
        self.current_day_cost = 0.0
        self.current_month_cost = 0.0
        
        # Cache for cost data
        self.cost_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Emergency shutoff
        self.emergency_stop = False
        
        print("✅ Cost Monitor initialized")
    
    def check_query_cost(self, bytes_to_process: int) -> Dict[str, Any]:
        """
        Check if a query is within cost limits
        
        Args:
            bytes_to_process: Estimated bytes the query will process
            
        Returns:
            Dict with approval status and details
        """
        estimated_cost = (bytes_to_process / 1_000_000_000_000) * 5.00  # $5 per TB
        
        # Check against limits
        if estimated_cost > self.thresholds.query_cost_limit:
            return {
                'approved': False,
                'reason': f'Query cost ${estimated_cost:.4f} exceeds limit ${self.thresholds.query_cost_limit}',
                'severity': AlertSeverity.CRITICAL
            }
        
        if bytes_to_process > self.thresholds.bytes_per_query_limit:
            return {
                'approved': False,
                'reason': f'Query size {bytes_to_process:,} bytes exceeds limit',
                'severity': AlertSeverity.CRITICAL
            }
        
        # Check daily budget
        if self.current_day_cost + estimated_cost > self.thresholds.daily_limit:
            return {
                'approved': False,
                'reason': f'Query would exceed daily budget (${self.current_day_cost:.2f} + ${estimated_cost:.2f} > ${self.thresholds.daily_limit})',
                'severity': AlertSeverity.CRITICAL
            }
        
        # Warning for expensive queries
        if estimated_cost > self.thresholds.query_cost_warning:
            return {
                'approved': True,
                'warning': f'High cost query: ${estimated_cost:.4f}',
                'severity': AlertSeverity.WARNING
            }
        
        return {
            'approved': True,
            'estimated_cost': estimated_cost,
            'severity': AlertSeverity.INFO
        }
    
    def update_usage(self, bytes_processed: int, cost: float):
        """
        Update usage counters
        
        Args:
            bytes_processed: Bytes processed by query
            cost: Estimated cost of query
        """
        self.current_hour_queries += 1
        self.current_day_queries += 1
        self.current_day_cost += cost
        self.current_month_cost += cost
        
        # Check if we've hit any limits
        self._check_limits()
    
    def _check_limits(self):
        """Check all limits and trigger alerts if needed"""
        
        alerts = []
        
        # Hourly checks
        if self.current_hour_queries > self.thresholds.queries_per_hour_limit:
            alerts.append({
                'type': 'hourly_query_limit',
                'message': f'Hourly query limit exceeded: {self.current_hour_queries}/{self.thresholds.queries_per_hour_limit}',
                'severity': AlertSeverity.WARNING
            })
        
        # Daily checks
        if self.current_day_queries > self.thresholds.queries_per_day_limit:
            alerts.append({
                'type': 'daily_query_limit',
                'message': f'Daily query limit exceeded: {self.current_day_queries}/{self.thresholds.queries_per_day_limit}',
                'severity': AlertSeverity.CRITICAL
            })
            self.emergency_stop = True
        
        if self.current_day_cost > self.thresholds.daily_limit:
            alerts.append({
                'type': 'daily_cost_limit',
                'message': f'Daily cost limit exceeded: ${self.current_day_cost:.2f}/${self.thresholds.daily_limit}',
                'severity': AlertSeverity.EMERGENCY
            })
            self.emergency_stop = True
        
        # Monthly checks
        if self.current_month_cost > self.thresholds.monthly_limit:
            alerts.append({
                'type': 'monthly_cost_limit',
                'message': f'Monthly cost limit exceeded: ${self.current_month_cost:.2f}/${self.thresholds.monthly_limit}',
                'severity': AlertSeverity.EMERGENCY
            })
            self.emergency_stop = True
        
        # Process alerts
        for alert in alerts:
            self._send_alert(alert)
    
    def _send_alert(self, alert: Dict):
        """Send cost alert"""
        print(f"🚨 COST ALERT [{alert['severity'].value}]: {alert['message']}")
        
        # In production, this would send to Slack, email, etc.
        if alert['severity'] in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            print("⛔ EMERGENCY: Pipeline operations suspended")
    
    def get_cost_status(self) -> Dict[str, Any]:
        """
        Get current cost status
        
        Returns:
            Dict with cost status information
        """
        # Calculate percentages
        daily_percentage = (self.current_day_cost / self.thresholds.daily_limit) * 100
        monthly_percentage = (self.current_month_cost / self.thresholds.monthly_limit) * 100
        
        # Determine status
        if daily_percentage >= 95 or monthly_percentage >= 95:
            status = CostStatus.EXCEEDED
        elif daily_percentage >= 80 or monthly_percentage >= 80:
            status = CostStatus.CRITICAL
        elif daily_percentage >= 50 or monthly_percentage >= 50:
            status = CostStatus.WARNING
        else:
            status = CostStatus.HEALTHY
        
        return {
            'status': status.value,
            'emergency_stop': self.emergency_stop,
            'current_hour': {
                'queries': self.current_hour_queries,
                'limit': self.thresholds.queries_per_hour_limit
            },
            'current_day': {
                'queries': self.current_day_queries,
                'query_limit': self.thresholds.queries_per_day_limit,
                'cost': self.current_day_cost,
                'cost_limit': self.thresholds.daily_limit,
                'percentage': daily_percentage,
                'remaining': self.thresholds.daily_limit - self.current_day_cost
            },
            'current_month': {
                'cost': self.current_month_cost,
                'limit': self.thresholds.monthly_limit,
                'percentage': monthly_percentage,
                'remaining': self.thresholds.monthly_limit - self.current_month_cost
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_cost_optimization_tips(self) -> List[Dict[str, str]]:
        """
        Get cost optimization recommendations
        
        Returns:
            List of optimization tips
        """
        tips = []
        
        # Check if queries are too frequent
        if self.current_hour_queries > 20:
            tips.append({
                'category': 'Query Frequency',
                'issue': 'High query frequency detected',
                'recommendation': 'Consider caching results for frequently run queries',
                'potential_savings': '$0.50-1.00/day'
            })
        
        # Check if we're close to limits
        status = self.get_cost_status()
        if status['current_day']['percentage'] > 70:
            tips.append({
                'category': 'Daily Budget',
                'issue': f"Using {status['current_day']['percentage']:.0f}% of daily budget",
                'recommendation': 'Review and optimize expensive queries',
                'potential_savings': '$1-2/day'
            })
        
        # Check for missing optimizations
        if self.bq:
            tips.append({
                'category': 'Table Optimization',
                'issue': 'Check if all tables are partitioned and clustered',
                'recommendation': 'Partition by date, cluster by common filter columns',
                'potential_savings': '60-90% reduction in query costs'
            })
        
        return tips
    
    def generate_cost_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive cost report
        
        Returns:
            Dict with cost report data
        """
        status = self.get_cost_status()
        tips = self.get_cost_optimization_tips()
        
        # Estimate monthly projection
        days_in_month = 30
        days_elapsed = datetime.now().day
        daily_average = self.current_month_cost / max(days_elapsed, 1)
        projected_monthly = daily_average * days_in_month
        
        report = {
            'summary': {
                'status': status['status'],
                'emergency_stop': status['emergency_stop'],
                'generated_at': datetime.now().isoformat()
            },
            'current_usage': {
                'today': {
                    'cost': f"${self.current_day_cost:.2f}",
                    'queries': self.current_day_queries,
                    'budget_used': f"{status['current_day']['percentage']:.1f}%"
                },
                'month': {
                    'cost': f"${self.current_month_cost:.2f}",
                    'projected': f"${projected_monthly:.2f}",
                    'budget_used': f"{status['current_month']['percentage']:.1f}%"
                }
            },
            'limits': {
                'daily': f"${self.thresholds.daily_limit}",
                'monthly': f"${self.thresholds.monthly_limit}",
                'per_query': f"${self.thresholds.query_cost_limit}"
            },
            'optimization_tips': tips,
            'recommendations': self._get_recommendations(status)
        }
        
        return report
    
    def _get_recommendations(self, status: Dict) -> List[str]:
        """Get actionable recommendations based on current status"""
        
        recommendations = []
        
        if status['status'] == 'exceeded':
            recommendations.append("🔴 URGENT: Costs have exceeded limits. Review and optimize immediately.")
        elif status['status'] == 'critical':
            recommendations.append("🟡 WARNING: Approaching cost limits. Consider optimizing queries.")
        elif status['status'] == 'healthy':
            recommendations.append("🟢 Costs are within healthy limits.")
        
        if status['current_day']['queries'] > 500:
            recommendations.append("Consider implementing query result caching to reduce redundant queries.")
        
        if self.current_hour_queries > 50:
            recommendations.append("High query frequency detected. Consider batching operations.")
        
        return recommendations
    
    def reset_hourly_counters(self):
        """Reset hourly counters (call this from scheduler)"""
        self.current_hour_queries = 0
        print(f"↻ Hourly counters reset at {datetime.now().strftime('%H:%M')}")
    
    def reset_daily_counters(self):
        """Reset daily counters (call this from scheduler)"""
        self.current_day_queries = 0
        self.current_day_cost = 0.0
        self.emergency_stop = False
        print(f"↻ Daily counters reset at {datetime.now().strftime('%Y-%m-%d')}")
    
    def reset_monthly_counters(self):
        """Reset monthly counters (call this from scheduler)"""
        self.current_month_cost = 0.0
        print(f"↻ Monthly counters reset at {datetime.now().strftime('%Y-%m')}")


if __name__ == "__main__":
    # Test cost monitor
    monitor = CostMonitor()
    
    print("\n💰 Testing Cost Monitor...")
    print("-" * 50)
    
    # Test query cost checking
    print("\n📊 Query Cost Checks:")
    
    # Small query
    small_query = monitor.check_query_cost(10_000_000)  # 10MB
    print(f"10MB query: {small_query}")
    
    # Large query
    large_query = monitor.check_query_cost(500_000_000_000)  # 500GB
    print(f"500GB query: {large_query}")
    
    # Update some usage
    monitor.update_usage(10_000_000, 0.00005)
    monitor.update_usage(20_000_000, 0.00010)
    
    # Get status
    print("\n📈 Cost Status:")
    status = monitor.get_cost_status()
    print(json.dumps(status, indent=2))
    
    # Get report
    print("\n📋 Cost Report:")
    report = monitor.generate_cost_report()
    print(json.dumps(report, indent=2))
    
    print("\n✅ Cost Monitor test complete!")