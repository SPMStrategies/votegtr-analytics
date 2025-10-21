"""
AI Analyzer - Claude API Integration
Analyzes weekly GA4 data with business context for CRO insights
"""

import os
from typing import Dict
import anthropic
from .business_context import BusinessContextManager

class AIAnalyzer:
    """AI-powered analytics analyzer using Claude"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.context_manager = BusinessContextManager()

        print("✅ AI Analyzer initialized with Claude API")

    def analyze_weekly_data(self, week_data: Dict) -> str:
        """
        Generate AI-powered CRO analysis

        Args:
            week_data: Aggregated weekly analytics data

        Returns:
            Markdown-formatted analysis report
        """
        print("\n🤖 Generating AI analysis with Claude...")

        # Fetch business context
        business_context = self.context_manager.fetch_context()
        context_text = self.context_manager.format_for_prompt(business_context)

        # Build analysis prompt
        prompt = self._build_analysis_prompt(context_text, week_data)

        # Call Claude API
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis = message.content[0].text
            print("✅ AI analysis complete")
            return analysis

        except Exception as e:
            print(f"❌ Error generating AI analysis: {e}")
            raise

    def _build_analysis_prompt(self, context: str, data: Dict) -> str:
        """Build detailed analysis prompt"""

        # Format data sections
        funnel_text = self._format_funnel_data(data.get('funnel', {}))
        conversions_text = self._format_conversions_data(data.get('conversions', {}))
        traffic_text = self._format_traffic_data(data.get('traffic', {}))
        pages_text = self._format_pages_data(data.get('pages', {}))
        device_text = self._format_device_data(data.get('devices', {}))

        prompt = f"""You are a conversion rate optimization expert analyzing weekly GA4 data.

{context}

# Weekly Analytics Data
**Period:** {data.get('date_range', 'Last 7 days')}

## Funnel Performance
{funnel_text}

## Conversions Summary
{conversions_text}

## Traffic Sources
{traffic_text}

## Page Performance
{pages_text}

## Device Breakdown
{device_text}

---

# Analysis Instructions

Using the business context above, provide a comprehensive CRO analysis in the following format:

## Critical Insights (Top 5)

List the 5 most important findings with impact statements. Use this format:
**[Finding Number]. [Title]** – [Detailed impact statement with specific numbers and business implications]

## Executive Summary

### Conversion Status
State whether the site is CONVERTING or NOT CONVERTING with specific conversion rate and volume.

### Biggest Single Leak
Identify where the most opportunity is being lost in the funnel. Be specific with percentages and user counts.

### Biggest Single Opportunity
What's the highest ROI fix based on the data? Explain expected impact.

## Funnel Analysis

Analyze stage-by-stage:
- Where are the biggest drop-offs?
- How does each stage compare to B2B lead-gen benchmarks (2-5% CVR)?
- What user behaviors predict conversion?

## Traffic Source Performance

Analyze each traffic source:
- Which channels drive quality traffic that converts?
- Which channels waste budget or have poor engagement?
- Recommendations for budget allocation

## Page-Level Analysis

Identify:
- Top performing pages (high conversion assistance)
- Underperforming pages (high traffic, low conversion)
- Content gaps or opportunities

## Device & Technical Insights

Compare desktop vs mobile vs tablet:
- Conversion rate differences
- UX issues indicated by behavior
- Technical optimization opportunities

## CRO Action Plan

Provide prioritized, actionable recommendations:

### High Priority (Implement This Week)
1. [Specific action] – [Expected impact with numbers] – [Implementation difficulty]

### Medium Priority (Implement This Month)
2. [Specific action] – [Expected impact]

### Low Priority (Consider for Future)
3. [Specific action] – [Expected impact]

---

**Important Guidelines:**
- Be specific with numbers (don't say "some users" - say "47 users")
- Compare to benchmarks and previous periods
- Tie recommendations to business goals from the vault context
- Focus on conversion optimization, not just traffic
- Explain WHY each recommendation will work based on the data
"""
        return prompt

    def _format_funnel_data(self, funnel: Dict) -> str:
        """Format funnel data for prompt"""
        if not funnel.get('funnel_stages'):
            return "No funnel data available"

        text = ""
        for stage in funnel['funnel_stages']:
            text += f"- **{stage['stage']}**: {stage['count']} events, {stage['users']} users"
            if 'drop_off_rate' in stage:
                text += f" (↓ {stage['drop_off_rate']}% drop-off)"
            text += "\n"

        return text

    def _format_conversions_data(self, conversions: Dict) -> str:
        """Format conversions for prompt"""
        if not conversions:
            return "No conversion data available"

        text = f"**Total Conversions:** {conversions.get('total', 0)}\n"
        text += f"**Conversion Rate:** {conversions.get('conversion_rate', 0)}%\n\n"
        text += "**Breakdown:**\n"

        for event in conversions.get('events', []):
            text += f"- {event['type']}: {event['count']} conversions ({event['users']} unique users)\n"

        return text

    def _format_traffic_data(self, traffic: Dict) -> str:
        """Format traffic sources for prompt"""
        if not traffic.get('channels'):
            return "No traffic data available"

        text = ""
        for channel in traffic['channels'][:10]:  # Top 10
            text += f"- **{channel['channel']}**: {channel['sessions']} sessions, "
            text += f"{channel['conversions']} conversions ({channel['conversion_rate']}%)\n"

        return text

    def _format_pages_data(self, pages: Dict) -> str:
        """Format page performance for prompt"""
        if not pages:
            return "No page data available"

        text = "**Top Pages:**\n"
        for page in pages.get('top_pages', [])[:10]:
            text += f"- {page['path']}: {page['views']} views, {page['users']} users\n"

        return text

    def _format_device_data(self, devices: Dict) -> str:
        """Format device breakdown for prompt"""
        if not devices:
            return "No device data available"

        text = ""
        for device in devices.get('breakdown', []):
            text += f"- **{device['device']}**: {device['sessions']} sessions, "
            text += f"{device['conversions']} conversions ({device['conversion_rate']}%)\n"

        return text
