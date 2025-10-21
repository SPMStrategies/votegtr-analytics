"""
Report Generator Module
Creates and sends automated reports
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from jinja2 import Template
import plotly.graph_objects as go
import plotly.io as pio
from dotenv import load_dotenv

from ga4_client import GA4Client
from bigquery_optimized import OptimizedBigQueryManager
from cost_monitor import CostMonitor
from query_optimizer import QueryOptimizer
from email_sender import EmailSender

load_dotenv()


class ReportGenerator:
    """Generates various types of reports"""
    
    def __init__(self):
        """Initialize report generator"""
        self.ga4 = GA4Client()
        self.bq = OptimizedBigQueryManager()
        self.cost_monitor = CostMonitor(self.bq)
        self.optimizer = QueryOptimizer()
        self.email_sender = EmailSender()
        
        # Report templates directory
        self.reports_dir = 'reports'
        os.makedirs(self.reports_dir, exist_ok=True)
        
        print("✅ Report Generator initialized")
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive daily report
        
        Returns:
            Dict with report data
        """
        print("\n📊 Generating Daily Report...")
        print("=" * 50)
        
        report_date = datetime.now().date()
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        report = {
            'metadata': {
                'report_type': 'daily',
                'generated_at': datetime.now().isoformat(),
                'report_date': str(report_date),
                'report_for': str(yesterday)
            },
            'executive_summary': {},
            'performance_metrics': {},
            'funnel_analysis': {},
            'attribution': {},
            'cost_analysis': {},
            'alerts': [],
            'recommendations': []
        }
        
        # 1. Executive Summary
        print("📈 Fetching executive summary...")
        report['executive_summary'] = self._get_executive_summary()
        
        # 2. Performance Metrics
        print("📊 Analyzing performance metrics...")
        report['performance_metrics'] = self._get_performance_metrics()
        
        # 3. Funnel Analysis
        print("🔄 Analyzing funnel...")
        report['funnel_analysis'] = self._get_funnel_analysis()
        
        # 4. Attribution Analysis
        print("🎯 Analyzing attribution...")
        report['attribution'] = self._get_attribution_analysis()
        
        # 5. Cost Analysis
        print("💰 Analyzing costs...")
        report['cost_analysis'] = self.cost_monitor.generate_cost_report()
        
        # 6. Generate Alerts
        print("🚨 Checking for alerts...")
        report['alerts'] = self._generate_alerts(report)
        
        # 7. Generate Recommendations
        print("💡 Generating recommendations...")
        report['recommendations'] = self._generate_recommendations(report)
        
        print("\n✅ Daily report generated successfully!")
        
        return report
    
    def _get_executive_summary(self) -> Dict[str, Any]:
        """Get executive summary metrics"""
        
        # Get yesterday's metrics
        metrics = self.ga4.get_daily_metrics(1)
        
        # Get week-over-week comparison
        last_week = self.ga4.get_daily_metrics(7)
        prev_week = self.ga4.get_daily_metrics(14)
        
        if metrics['daily_metrics']:
            yesterday = metrics['daily_metrics'][0]
        else:
            yesterday = {'users': 0, 'sessions': 0, 'conversions': 0}
        
        # Calculate changes
        wow_sessions = 0
        if last_week['totals']['total_sessions'] > 0 and len(prev_week['daily_metrics']) > 7:
            prev_week_sessions = sum(d['sessions'] for d in prev_week['daily_metrics'][:7])
            if prev_week_sessions > 0:
                wow_sessions = ((last_week['totals']['total_sessions'] - prev_week_sessions) / prev_week_sessions) * 100
        
        return {
            'yesterday': {
                'users': yesterday.get('users', 0),
                'sessions': yesterday.get('sessions', 0),
                'page_views': yesterday.get('page_views', 0),
                'conversions': yesterday.get('conversions', 0),
                'bounce_rate': f"{yesterday.get('bounce_rate', 0):.1f}%"
            },
            'last_7_days': {
                'total_users': last_week['totals']['total_users'],
                'total_sessions': last_week['totals']['total_sessions'],
                'total_conversions': last_week['totals']['total_conversions'],
                'avg_bounce_rate': f"{last_week['totals']['avg_bounce_rate']:.1f}%"
            },
            'trends': {
                'sessions_wow': f"{wow_sessions:+.1f}%",
                'status': 'growing' if wow_sessions > 0 else 'declining'
            }
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        
        # Get daily trend
        daily_data = self.ga4.get_daily_metrics(7)
        
        # Get top pages
        top_pages = self.ga4.get_top_pages(limit=5)
        
        # Get real-time users
        realtime = self.ga4.get_real_time_users()
        
        return {
            'daily_trend': [
                {
                    'date': d['date'],
                    'sessions': d['sessions'],
                    'conversions': d['conversions']
                }
                for d in daily_data['daily_metrics']
            ],
            'top_pages': [
                {
                    'path': p['path'],
                    'views': p['views'],
                    'users': p['users']
                }
                for p in top_pages[:5]
            ],
            'current_active_users': realtime['total_active_users']
        }
    
    def _get_funnel_analysis(self) -> Dict[str, Any]:
        """Get funnel analysis with separated stages and conversions"""

        funnel = self.ga4.get_funnel_metrics()

        # Format funnel stages (user journey)
        stages_formatted = []
        for stage in funnel.get('funnel_stages', []):
            stages_formatted.append({
                'stage': stage['stage'],
                'event': stage['event'],
                'count': stage['count'],
                'users': stage['users'],
                'progression_rate': f"{stage.get('progression_rate', 100):.1f}%",
                'drop_off_rate': f"{stage.get('drop_off_rate', 0):.1f}%"
            })

        # Format conversions
        conversions_data = funnel.get('conversions', {})
        conversions_formatted = []
        for conv in conversions_data.get('events', []):
            conversions_formatted.append({
                'type': conv['type'],
                'event': conv['event'],
                'count': conv['count'],
                'users': conv['users']
            })

        # Find biggest drop-off
        biggest_dropoff = "N/A"
        if stages_formatted:
            max_dropoff_stage = max(stages_formatted, key=lambda x: float(x['drop_off_rate'].rstrip('%')))
            biggest_dropoff = max_dropoff_stage['stage']

        return {
            'stages': stages_formatted,
            'conversions': {
                'total': conversions_data.get('total', 0),
                'conversion_rate': f"{conversions_data.get('conversion_rate', 0):.2f}%",
                'events': conversions_formatted
            },
            'biggest_dropoff': biggest_dropoff,
            'total_sessions': funnel.get('total_sessions', 0)
        }
    
    def _get_attribution_analysis(self) -> Dict[str, Any]:
        """Get attribution analysis"""
        
        attribution = self.ga4.get_attribution_data()
        
        # Get top channels
        top_channels = sorted(
            attribution['channels'],
            key=lambda x: x['sessions'],
            reverse=True
        )[:5]
        
        # Calculate channel efficiency
        for channel in top_channels:
            if channel['sessions'] > 0:
                channel['efficiency'] = channel['conversions'] / channel['sessions']
            else:
                channel['efficiency'] = 0
        
        best_channel = max(top_channels, key=lambda x: x['efficiency']) if top_channels else None
        
        return {
            'utm_coverage': f"{attribution['utm_coverage']:.1f}%",
            'total_conversions': attribution['total_conversions'],
            'top_channels': [
                {
                    'channel': ch['channel'],
                    'sessions': ch['sessions'],
                    'conversions': ch['conversions'],
                    'conversion_rate': f"{ch['conversion_rate']:.2f}%"
                }
                for ch in top_channels
            ],
            'best_performing': best_channel['channel'] if best_channel else "N/A"
        }
    
    def _generate_alerts(self, report: Dict) -> List[Dict]:
        """Generate alerts based on report data"""
        
        alerts = []
        
        # Check conversion rate
        if report['executive_summary']['yesterday']['conversions'] == 0:
            if report['executive_summary']['yesterday']['sessions'] > 10:
                alerts.append({
                    'type': 'conversion',
                    'severity': 'warning',
                    'message': 'No conversions yesterday despite having sessions'
                })
        
        # Check bounce rate
        bounce_rate = float(report['executive_summary']['yesterday']['bounce_rate'].rstrip('%'))
        if bounce_rate > 70:
            alerts.append({
                'type': 'bounce_rate',
                'severity': 'warning',
                'message': f'High bounce rate: {bounce_rate:.1f}%'
            })
        
        # Check UTM coverage
        utm_coverage = float(report['attribution']['utm_coverage'].rstrip('%'))
        if utm_coverage < 75:
            alerts.append({
                'type': 'attribution',
                'severity': 'info',
                'message': f'Low UTM coverage: {utm_coverage:.1f}% - consider adding UTM tags'
            })
        
        # Check costs
        if report['cost_analysis']['summary']['status'] in ['critical', 'exceeded']:
            alerts.append({
                'type': 'cost',
                'severity': 'critical',
                'message': 'Cost limits approaching or exceeded'
            })
        
        return alerts
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Based on funnel
        if report['funnel_analysis']['stages']:
            worst_dropoff = report['funnel_analysis']['biggest_dropoff']
            recommendations.append(f"Focus on improving '{worst_dropoff}' stage - highest drop-off rate")
        
        # Based on attribution
        utm_coverage = float(report['attribution']['utm_coverage'].rstrip('%'))
        if utm_coverage < 75:
            recommendations.append("Add UTM parameters to all marketing links to improve attribution")
        
        # Based on performance
        if report['executive_summary']['trends']['status'] == 'declining':
            recommendations.append("Traffic is declining week-over-week - consider increasing marketing efforts")
        
        # Based on costs
        cost_tips = report['cost_analysis'].get('optimization_tips', [])
        if cost_tips:
            recommendations.append(cost_tips[0].get('recommendation', ''))
        
        # Based on conversion rate
        if report['executive_summary']['yesterday']['conversions'] == 0:
            recommendations.append("No conversions detected - verify tracking implementation")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def create_html_report(self, report_data: Dict) -> str:
        """
        Create HTML version of report
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            HTML string
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>VOTEGTR Daily Report - {{ report_date }}</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }
                .metric-card {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }
                .metric-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }
                .metric-box {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    text-align: center;
                }
                .metric-value {
                    font-size: 2em;
                    font-weight: bold;
                    color: #667eea;
                }
                .metric-label {
                    font-size: 0.9em;
                    color: #666;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .alert {
                    padding: 12px;
                    border-radius: 6px;
                    margin: 10px 0;
                }
                .alert-warning {
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                .alert-critical {
                    background: #f8d7da;
                    border-left: 4px solid #dc3545;
                }
                .alert-info {
                    background: #d1ecf1;
                    border-left: 4px solid #17a2b8;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }
                th, td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background: #f8f9fa;
                    font-weight: 600;
                }
                .recommendation {
                    padding: 10px;
                    margin: 8px 0;
                    background: #e7f3ff;
                    border-left: 3px solid #2196F3;
                    border-radius: 4px;
                }
                .trend-up {
                    color: #28a745;
                }
                .trend-down {
                    color: #dc3545;
                }
                .footer {
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 VOTEGTR Daily Analytics Report</h1>
                <p>{{ report_date }} | Generated at {{ generated_at }}</p>
            </div>
            
            <div class="metric-card">
                <h2>📈 Executive Summary</h2>
                <div class="metric-grid">
                    <div class="metric-box">
                        <div class="metric-value">{{ yesterday_sessions }}</div>
                        <div class="metric-label">Sessions</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{{ yesterday_users }}</div>
                        <div class="metric-label">Users</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{{ yesterday_conversions }}</div>
                        <div class="metric-label">Conversions</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{{ bounce_rate }}</div>
                        <div class="metric-label">Bounce Rate</div>
                    </div>
                </div>
                <p><strong>7-Day Trend:</strong> <span class="{{ trend_class }}">{{ trend_indicator }}</span></p>
            </div>
            
            <div class="metric-card">
                <h2>🔄 Funnel Performance</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Stage</th>
                            <th>Count</th>
                            <th>Conversion Rate</th>
                            <th>Drop-off</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for stage in funnel_stages %}
                        <tr>
                            <td>{{ stage.stage }}</td>
                            <td>{{ stage.count }}</td>
                            <td>{{ stage.conversion_rate }}</td>
                            <td>{{ stage.dropoff_rate }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="metric-card">
                <h2>🎯 Attribution Analysis</h2>
                <p><strong>UTM Coverage:</strong> {{ utm_coverage }}</p>
                <table>
                    <thead>
                        <tr>
                            <th>Channel</th>
                            <th>Sessions</th>
                            <th>Conversions</th>
                            <th>Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for channel in top_channels %}
                        <tr>
                            <td>{{ channel.channel }}</td>
                            <td>{{ channel.sessions }}</td>
                            <td>{{ channel.conversions }}</td>
                            <td>{{ channel.conversion_rate }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="metric-card">
                <h2>💰 Cost Analysis</h2>
                <div class="metric-grid">
                    <div class="metric-box">
                        <div class="metric-value">{{ daily_cost }}</div>
                        <div class="metric-label">Today's Cost</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{{ monthly_cost }}</div>
                        <div class="metric-label">Month to Date</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{{ budget_status }}</div>
                        <div class="metric-label">Budget Status</div>
                    </div>
                </div>
            </div>
            
            {% if alerts %}
            <div class="metric-card">
                <h2>🚨 Alerts</h2>
                {% for alert in alerts %}
                <div class="alert alert-{{ alert.severity }}">
                    <strong>{{ alert.type|upper }}:</strong> {{ alert.message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="metric-card">
                <h2>💡 Recommendations</h2>
                {% for rec in recommendations %}
                <div class="recommendation">
                    {{ loop.index }}. {{ rec }}
                </div>
                {% endfor %}
            </div>
            
            <div class="footer">
                <p>VOTEGTR Analytics System | Report generated automatically</p>
                <p>Questions? Check the dashboard for real-time data.</p>
            </div>
        </body>
        </html>
        """
        
        # Prepare template data
        template_data = {
            'report_date': report_data['metadata']['report_for'],
            'generated_at': datetime.now().strftime('%I:%M %p'),
            'yesterday_sessions': report_data['executive_summary']['yesterday']['sessions'],
            'yesterday_users': report_data['executive_summary']['yesterday']['users'],
            'yesterday_conversions': report_data['executive_summary']['yesterday']['conversions'],
            'bounce_rate': report_data['executive_summary']['yesterday']['bounce_rate'],
            'trend_indicator': report_data['executive_summary']['trends']['sessions_wow'],
            'trend_class': 'trend-up' if report_data['executive_summary']['trends']['status'] == 'growing' else 'trend-down',
            'funnel_stages': report_data['funnel_analysis']['stages'][:5],
            'utm_coverage': report_data['attribution']['utm_coverage'],
            'top_channels': report_data['attribution']['top_channels'],
            'daily_cost': report_data['cost_analysis']['current_usage']['today']['cost'],
            'monthly_cost': report_data['cost_analysis']['current_usage']['month']['cost'],
            'budget_status': report_data['cost_analysis']['summary']['status'].upper(),
            'alerts': report_data['alerts'],
            'recommendations': report_data['recommendations']
        }
        
        # Render template
        template = Template(html_template)
        html = template.render(**template_data)
        
        return html
    
    def save_report(self, report_data: Dict, format: str = 'json') -> str:
        """
        Save report to file
        
        Args:
            report_data: Report data
            format: Output format (json, html)
            
        Returns:
            File path
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filename = f"{self.reports_dir}/daily_report_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
        
        elif format == 'html':
            filename = f"{self.reports_dir}/daily_report_{timestamp}.html"
            html = self.create_html_report(report_data)
            with open(filename, 'w') as f:
                f.write(html)
        
        print(f"📁 Report saved: {filename}")
        return filename
    
    def generate_and_save_daily_report(self, send_email: bool = False) -> Tuple[str, str]:
        """
        Generate and save daily report in multiple formats
        
        Args:
            send_email: Whether to send the report via email
            
        Returns:
            Tuple of (json_path, html_path)
        """
        # Generate report
        report = self.generate_daily_report()
        
        # Save in both formats
        json_path = self.save_report(report, 'json')
        html_path = self.save_report(report, 'html')
        
        # Send email if requested
        if send_email and self.email_sender.enabled:
            html_content = self.create_html_report(report)
            success = self.email_sender.send_daily_report(html_content, json_path)
            if not success:
                print("⚠️  Failed to send email report")
        elif send_email and not self.email_sender.enabled:
            print("📧 Email sending requested but SendGrid not configured")
        
        return json_path, html_path


if __name__ == "__main__":
    # Test report generator
    try:
        generator = ReportGenerator()
        
        print("\n📊 Testing Report Generator...")
        print("-" * 50)
        
        # Generate daily report
        json_path, html_path = generator.generate_and_save_daily_report()
        
        print(f"\n✅ Reports generated successfully!")
        print(f"   JSON: {json_path}")
        print(f"   HTML: {html_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")