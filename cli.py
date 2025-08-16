#!/usr/bin/env python3
"""
VOTEGTR Analytics CLI
Main command-line interface for the analytics system
"""

import os
import sys
import click
import json
from datetime import datetime, timedelta
from tabulate import tabulate
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ga4_client import GA4Client
from bigquery_optimized import OptimizedBigQueryManager
from data_pipeline import DataPipeline
from report_generator import ReportGenerator
from cost_monitor import CostMonitor
from query_optimizer import QueryOptimizer

load_dotenv()


@click.group()
@click.version_option(version='1.0.0', prog_name='VOTEGTR Analytics')
def cli():
    """VOTEGTR Analytics Management System"""
    pass


@cli.command()
def dashboard():
    """View real-time dashboard metrics"""
    try:
        ga4 = GA4Client()
        cost_monitor = CostMonitor()
        
        click.clear()
        click.secho("=" * 60, fg='blue')
        click.secho("           VOTEGTR ANALYTICS DASHBOARD", fg='blue', bold=True)
        click.secho("=" * 60, fg='blue')
        click.echo()
        
        # Real-time users
        realtime = ga4.get_real_time_users()
        click.secho(f"👥 Active Users Now: {realtime['total_active_users']}", fg='green', bold=True)
        
        # Today's metrics
        today_metrics = ga4.get_daily_metrics(1)
        if today_metrics['daily_metrics']:
            today = today_metrics['daily_metrics'][0]
            click.echo()
            click.secho("📊 Today's Performance:", fg='yellow', bold=True)
            metrics_table = [
                ['Sessions', today['sessions']],
                ['Users', today['users']],
                ['Page Views', today['page_views']],
                ['Conversions', today['conversions']],
                ['Bounce Rate', f"{today['bounce_rate']:.1f}%"],
            ]
            click.echo(tabulate(metrics_table, headers=['Metric', 'Value'], tablefmt='simple'))
        
        # Cost status
        cost_status = cost_monitor.get_cost_status()
        click.echo()
        click.secho("💰 Cost Status:", fg='yellow', bold=True)
        cost_table = [
            ['Daily Cost', f"${cost_status['current_day']['cost']:.2f}"],
            ['Daily Budget', f"${cost_status['current_day']['cost_limit']:.2f}"],
            ['Budget Used', f"{cost_status['current_day']['percentage']:.1f}%"],
            ['Status', cost_status['status'].upper()]
        ]
        click.echo(tabulate(cost_table, headers=['Metric', 'Value'], tablefmt='simple'))
        
        # Funnel summary
        funnel = ga4.get_funnel_metrics('today', 'today')
        if funnel['stages']:
            click.echo()
            click.secho("🔄 Today's Funnel:", fg='yellow', bold=True)
            funnel_table = [
                [s['stage'][:20], s['count'], f"{s['conversion_rate']:.1f}%"]
                for s in funnel['stages'][:5]
            ]
            click.echo(tabulate(funnel_table, headers=['Stage', 'Count', 'Rate'], tablefmt='simple'))
        
        click.echo()
        click.secho("✅ Dashboard updated at " + datetime.now().strftime('%I:%M %p'), fg='green')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cli.group()
def report():
    """Generate and manage reports"""
    pass


@report.command()
@click.option('--send-email', is_flag=True, help='Send report via email')
@click.option('--format', type=click.Choice(['json', 'html', 'both']), default='both')
def daily(send_email, format):
    """Generate daily report"""
    try:
        generator = ReportGenerator()
        
        click.secho("📊 Generating daily report...", fg='yellow')
        
        # Generate and save report
        json_path, html_path = generator.generate_and_save_daily_report(send_email=send_email)
        
        click.secho(f"✅ Report saved:", fg='green')
        click.echo(f"   JSON: {json_path}")
        click.echo(f"   HTML: {html_path}")
        
        if send_email:
            if generator.email_sender.enabled:
                click.secho(f"📧 Report emailed to {generator.email_sender.default_to}", fg='green')
            else:
                click.secho("⚠️  Email not sent - SendGrid not configured", fg='yellow')
                click.echo("   Add your SendGrid API key to .env to enable email")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@report.command()
@click.option('--days', default=7, help='Number of days to include')
def weekly(days):
    """Generate weekly report"""
    try:
        ga4 = GA4Client()
        
        click.secho(f"📊 Generating {days}-day report...", fg='yellow')
        
        # Get metrics
        metrics = ga4.get_daily_metrics(days)
        attribution = ga4.get_attribution_data(f'{days}daysAgo', 'today')
        
        # Display summary
        click.echo()
        click.secho(f"📈 {days}-Day Summary:", fg='blue', bold=True)
        summary_table = [
            ['Total Sessions', metrics['totals']['total_sessions']],
            ['Total Users', metrics['totals']['total_users']],
            ['Total Conversions', metrics['totals']['total_conversions']],
            ['Avg Bounce Rate', f"{metrics['totals']['avg_bounce_rate']:.1f}%"],
            ['UTM Coverage', f"{attribution['utm_coverage']:.1f}%"]
        ]
        click.echo(tabulate(summary_table, headers=['Metric', 'Value'], tablefmt='simple'))
        
        click.secho(f"\n✅ Report generated successfully", fg='green')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cli.group()
def funnel():
    """Analyze conversion funnel"""
    pass


@funnel.command()
@click.option('--period', type=click.Choice(['today', 'yesterday', '7days', '30days']), default='7days')
def show(period):
    """Show funnel performance"""
    try:
        ga4 = GA4Client()
        
        # Map period to date range
        date_ranges = {
            'today': ('today', 'today'),
            'yesterday': ('yesterday', 'yesterday'),
            '7days': ('7daysAgo', 'today'),
            '30days': ('30daysAgo', 'today')
        }
        
        start, end = date_ranges[period]
        
        click.secho(f"🔄 Funnel Analysis ({period})", fg='blue', bold=True)
        click.echo()
        
        funnel = ga4.get_funnel_metrics(start, end)
        
        if funnel['stages']:
            # Calculate drop-offs
            for i, stage in enumerate(funnel['stages']):
                if i == 0:
                    dropoff = 0
                    bar_length = 40
                else:
                    prev = funnel['stages'][i-1]['count']
                    dropoff = ((prev - stage['count']) / prev * 100) if prev > 0 else 0
                    bar_length = int(40 * stage['conversion_rate'] / 100)
                
                # Visual funnel
                bar = '█' * bar_length + '░' * (40 - bar_length)
                
                click.echo(f"{stage['stage'][:20]:<20} {bar} {stage['count']:>6} ({stage['conversion_rate']:>5.1f}%)")
                
                if i < len(funnel['stages']) - 1 and dropoff > 0:
                    click.echo(f"{'':20} ↓ {dropoff:.1f}% drop-off", )
            
            click.echo()
            click.secho(f"Total Conversion Rate: {funnel['stages'][-1]['conversion_rate']:.2f}%", 
                       fg='green' if funnel['stages'][-1]['conversion_rate'] > 1 else 'yellow')
        else:
            click.secho("No funnel data available", fg='yellow')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cli.group()
def data():
    """Data pipeline operations"""
    pass


@data.command()
@click.option('--full', is_flag=True, help='Run full sync (all data types)')
def sync(full):
    """Sync data from GA4 to BigQuery"""
    try:
        pipeline = DataPipeline()
        
        if full:
            click.secho("🚀 Starting full data sync...", fg='yellow')
            results = pipeline.run_full_sync()
            
            # Show results
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            
            if success_count == total_count:
                click.secho(f"✅ All {total_count} sync operations successful!", fg='green')
            else:
                click.secho(f"⚠️  {success_count}/{total_count} operations successful", fg='yellow')
                for name, success in results.items():
                    if not success:
                        click.echo(f"   ❌ {name} failed")
        else:
            click.secho("⏰ Running hourly sync...", fg='yellow')
            success = pipeline.run_hourly_sync()
            if success:
                click.secho("✅ Hourly sync complete", fg='green')
            else:
                click.secho("❌ Hourly sync failed", fg='red')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@data.command()
def health():
    """Check data health status"""
    try:
        pipeline = DataPipeline()
        
        click.secho("🏥 Checking Data Health...", fg='yellow')
        click.echo()
        
        health = pipeline.check_data_health()
        
        # Display status
        status_color = {
            'healthy': 'green',
            'warning': 'yellow',
            'critical': 'red',
            'error': 'red'
        }
        
        click.secho(f"Overall Status: {health['overall'].upper()}", 
                   fg=status_color.get(health['overall'], 'white'), bold=True)
        click.echo()
        
        # Component status
        click.secho("Component Status:", fg='blue')
        components = [
            ['GA4', health['ga4_status'].upper()],
            ['BigQuery', health['bigquery_status'].upper()]
        ]
        click.echo(tabulate(components, headers=['Component', 'Status'], tablefmt='simple'))
        
        # Issues
        if health['issues']:
            click.echo()
            click.secho("Issues Found:", fg='yellow')
            for issue in health['issues']:
                click.echo(f"  ⚠️  {issue}")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cli.group()
def cost():
    """Cost monitoring and optimization"""
    pass


@cost.command()
def status():
    """Show current cost status"""
    try:
        monitor = CostMonitor()
        
        status = monitor.get_cost_status()
        
        click.secho("💰 Cost Status", fg='blue', bold=True)
        click.echo()
        
        # Status indicator
        status_colors = {
            'healthy': 'green',
            'warning': 'yellow',
            'critical': 'red',
            'exceeded': 'red'
        }
        
        click.secho(f"Status: {status['status'].upper()}", 
                   fg=status_colors.get(status['status'], 'white'), bold=True)
        
        if status['emergency_stop']:
            click.secho("⛔ EMERGENCY STOP ACTIVE", fg='red', bold=True, blink=True)
        
        click.echo()
        
        # Daily metrics
        click.secho("Today:", fg='yellow')
        daily_table = [
            ['Queries', f"{status['current_day']['queries']}/{status['current_day']['query_limit']}"],
            ['Cost', f"${status['current_day']['cost']:.2f}/${status['current_day']['cost_limit']:.2f}"],
            ['Budget Used', f"{status['current_day']['percentage']:.1f}%"],
            ['Remaining', f"${status['current_day']['remaining']:.2f}"]
        ]
        click.echo(tabulate(daily_table, tablefmt='simple'))
        
        click.echo()
        
        # Monthly metrics
        click.secho("This Month:", fg='yellow')
        monthly_table = [
            ['Cost', f"${status['current_month']['cost']:.2f}/${status['current_month']['limit']:.2f}"],
            ['Budget Used', f"{status['current_month']['percentage']:.1f}%"],
            ['Remaining', f"${status['current_month']['remaining']:.2f}"]
        ]
        click.echo(tabulate(monthly_table, tablefmt='simple'))
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cost.command()
def optimize():
    """Get cost optimization recommendations"""
    try:
        monitor = CostMonitor()
        optimizer = QueryOptimizer()
        
        click.secho("🔧 Cost Optimization Analysis", fg='blue', bold=True)
        click.echo()
        
        # Get recommendations
        tips = monitor.get_cost_optimization_tips()
        opt_report = optimizer.get_optimization_report()
        
        # Display tips
        if tips:
            click.secho("Optimization Opportunities:", fg='yellow')
            for i, tip in enumerate(tips, 1):
                click.echo(f"\n{i}. {tip['category']}")
                click.echo(f"   Issue: {tip['issue']}")
                click.echo(f"   Fix: {tip['recommendation']}")
                click.echo(f"   Savings: {tip['potential_savings']}")
        
        # Cache performance
        click.echo()
        click.secho("Cache Performance:", fg='yellow')
        cache_table = [
            ['Hit Rate', opt_report['cache_performance']['hit_rate']],
            ['Total Hits', opt_report['cache_performance']['total_hits']],
            ['Cached Queries', opt_report['cache_performance']['cached_queries']],
            ['Memory Usage', opt_report['cache_performance']['memory_usage']]
        ]
        click.echo(tabulate(cache_table, tablefmt='simple'))
        
        click.echo()
        click.secho(f"💡 Potential savings: {opt_report['cost_reduction_potential']}", fg='green')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cli.group()
def alerts():
    """Alert management"""
    pass


@alerts.command()
def check():
    """Check for current alerts"""
    try:
        ga4 = GA4Client()
        monitor = CostMonitor()
        
        click.secho("🚨 Checking for alerts...", fg='yellow')
        click.echo()
        
        alerts_found = []
        
        # Check data quality
        quality = ga4.check_data_quality()
        if quality['missing_events']:
            alerts_found.append({
                'type': 'DATA',
                'severity': 'WARNING',
                'message': f"Missing events: {', '.join(quality['missing_events'])}"
            })
        
        if quality['attribution_rate'] < 75:
            alerts_found.append({
                'type': 'ATTRIBUTION',
                'severity': 'INFO',
                'message': f"Low attribution rate: {quality['attribution_rate']:.1f}%"
            })
        
        # Check costs
        cost_status = monitor.get_cost_status()
        if cost_status['status'] in ['critical', 'exceeded']:
            alerts_found.append({
                'type': 'COST',
                'severity': 'CRITICAL',
                'message': f"Cost status: {cost_status['status'].upper()}"
            })
        
        # Display alerts
        if alerts_found:
            for alert in alerts_found:
                severity_colors = {
                    'INFO': 'blue',
                    'WARNING': 'yellow',
                    'CRITICAL': 'red'
                }
                
                click.secho(f"[{alert['severity']}] {alert['type']}: {alert['message']}", 
                           fg=severity_colors.get(alert['severity'], 'white'))
        else:
            click.secho("✅ No alerts - all systems healthy", fg='green')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


@cli.command()
def setup():
    """Initial setup and configuration check"""
    try:
        click.secho("🔧 Running Setup Check...", fg='yellow')
        click.echo()
        
        checks = []
        
        # Check environment variables
        env_vars = ['GA4_PROPERTY_ID', 'GOOGLE_APPLICATION_CREDENTIALS', 'GCP_PROJECT_ID']
        for var in env_vars:
            value = os.getenv(var)
            if value:
                checks.append([var, '✅', value[:20] + '...' if len(value) > 20 else value])
            else:
                checks.append([var, '❌', 'Not set'])
        
        click.secho("Environment Variables:", fg='blue')
        click.echo(tabulate(checks, headers=['Variable', 'Status', 'Value'], tablefmt='simple'))
        
        # Test connections
        click.echo()
        click.secho("Testing Connections:", fg='blue')
        
        # GA4
        try:
            ga4 = GA4Client()
            realtime = ga4.get_real_time_users()
            click.echo("GA4 API: ✅ Connected")
        except Exception as e:
            click.echo(f"GA4 API: ❌ {str(e)[:50]}")
        
        # BigQuery
        try:
            bq = OptimizedBigQueryManager()
            click.echo("BigQuery: ✅ Connected")
        except Exception as e:
            click.echo(f"BigQuery: ❌ {str(e)[:50]}")
        
        click.echo()
        click.secho("✅ Setup check complete", fg='green')
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')


if __name__ == '__main__':
    cli()