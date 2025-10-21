# VOTEGTR Analytics Transformation - Implementation Status

## Project Overview
Transforming votegtr-analytics from a dashboard-focused system to an AI-powered weekly reporting system with:
- Funnel tracking that separates journey stages from conversions
- Dynamic business context from votegtr-vault repo
- Claude AI-powered analysis
- VOTEGTR-GAds style date-stamped folders and markdown reports

---

## ✅ COMPLETED (Phase 1)

### 1. Funnel Tracking Fix ✅
**File:** `src/ga4_client.py`

**What was fixed:**
- Replaced hardcoded event names that didn't exist with actual tracked events
- Separated funnel stages (user journey) from conversion events (goals)
- Added stage-to-stage progression and drop-off calculations

**Results:**
```
Funnel Stages (30 days):
- Site Visit: 316 sessions
- Content View: 534 page views
- Engaged Session: 404 engaged users
- Interaction: 14 clicks

Conversions: 11 total (3.48% CVR)
- Form Submission: 6
- Landing Page Conversion: 3
- Learning Center Signup: 1
- Purchase: 1
```

**Before:** Showed 0-1 conversions
**After:** Shows all 11 conversions properly separated

### 2. Report Generator Update ✅
**File:** `src/report_generator.py`

Updated `_get_funnel_analysis()` to handle new funnel structure with separated stages and conversions.

### 3. Folder Structure ✅
Created new directory structure:
```
votegtr-analytics/
├── data/                  # For daily data collection
├── analysis/              # For AI-generated reports
├── src/
│   ├── analyzers/         # AI analysis modules
│   ├── collectors/        # Data collection modules
│   └── generators/        # Report generation modules
```

### 4. Business Context Manager ✅
**File:** `src/analyzers/business_context.py`

- Fetches business context from votegtr-vault repo
- Supports both live fetch and cached loading
- Formats context for AI prompts
- Dynamically updates as vault repo evolves

### 5. Dependencies Updated ✅
**File:** `requirements.txt`

Added:
- `anthropic>=0.34.0` (Claude API)
- `markdown>=3.5.0` (Markdown to HTML conversion)

### 6. Environment Configuration ✅
**File:** `.env.example`

Added:
- `ANTHROPIC_API_KEY` for Claude AI integration

---

## 🚧 IN PROGRESS (Phase 2)

### High Priority Modules

#### 1. AI Analyzer (NEXT)
**File to create:** `src/analyzers/ai_analyzer.py`

**Purpose:**
- Integrate with Claude API
- Fetch business context from vault
- Generate CRO-focused weekly analysis
- Use structured prompts for consistent output

**Key features:**
```python
class AIAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(...)
        self.context_manager = BusinessContextManager()

    def analyze_weekly_data(self, week_data: Dict) -> str:
        # Fetch vault context
        # Build detailed CRO prompt
        # Call Claude API
        # Return markdown analysis
```

#### 2. GA4 Data Collector
**File to create:** `src/collectors/ga4_data_collector.py`

**Purpose:**
- Pull comprehensive daily data from GA4
- Collect funnel, traffic, pages, devices data
- Save to date-stamped JSON files

**Key methods:**
```python
class GA4DataCollector:
    def collect_daily_data(self, date='yesterday') -> Dict:
        # Pull all GA4 metrics for the date
        # Return structured data dict
```

#### 3. Data Organizer
**File to create:** `src/collectors/data_organizer.py`

**Purpose:**
- Organize data into `data/YYYY-MM-DD/` folders
- Aggregate 7 days of data for weekly analysis
- Save individual JSON files per metric type

**Key methods:**
```python
class DataOrganizer:
    def save_daily_data(self, date: str, data: Dict):
        # Save to data/YYYY-MM-DD/*.json

    def get_week_data(self, end_date: str) -> Dict:
        # Aggregate 7 days of JSON files
```

#### 4. Report Builder
**File to create:** `src/generators/report_builder.py`

**Purpose:**
- Convert markdown to HTML
- Apply email templates
- Save to analysis/ folder

**Key methods:**
```python
class ReportBuilder:
    def markdown_to_html(self, markdown: str) -> str:
        # Convert with styling for email

    def save_report(self, markdown: str, html: str, date: str):
        # Save to analysis/YYYY-MM-DD-weekly-analysis.md
```

#### 5. CLI Commands
**File to update:** `cli.py`

**New commands to add:**
```python
@cli.command()
def collect():
    """Collect today's GA4 data"""
    # Use GA4DataCollector + DataOrganizer

@cli.command()
@click.option('--send-email', is_flag=True)
def analyze(send_email):
    """Generate AI weekly analysis"""
    # Use DataOrganizer + AIAnalyzer + ReportBuilder
```

---

## 📅 TODO (Phase 3 - Automation)

### GitHub Actions Workflows

#### 1. Daily Collection
**File to create:** `.github/workflows/daily-collection.yml`

**Schedule:** 7 AM ET daily (cron: '0 11 * * *')

**Steps:**
1. Checkout repo
2. Setup Python 3.11
3. Install dependencies
4. Setup Google credentials
5. Run `python cli.py collect`
6. Commit data files to repo

#### 2. Weekly Analysis
**File to create:** `.github/workflows/weekly-analysis.yml`

**Schedule:** 8 AM ET Mondays (cron: '0 12 * * 1')

**Steps:**
1. Checkout repo (full history for 7 days data)
2. Setup Python 3.11
3. Install dependencies
4. Setup credentials (Google + Anthropic)
5. Run `python cli.py analyze --send-email`
6. Commit analysis markdown to repo

**Required GitHub Secrets:**
- `GOOGLE_CREDENTIALS` ✅ (already exists)
- `GA4_PROPERTY_ID` ✅ (already exists)
- `SENDGRID_API_KEY` ✅ (already exists)
- `REPORT_EMAIL_TO` ✅ (already exists)
- `ANTHROPIC_API_KEY` ❌ (need to add)

---

## 🧹 Cleanup Tasks

### Remove Dashboard Components
**Files to delete:**
- `api/dashboard.py`
- `src/dashboard_builder.py`

**File to update:**
- `cli.py` - Remove dashboard command

---

## 🎯 Success Criteria

After full implementation, the system should:

1. **✅ Show 11 conversions** (not 0) - DONE
2. **✅ Separate funnel stages from conversions** - DONE
3. **📊 Collect data daily** to `data/YYYY-MM-DD/`
4. **🤖 Generate AI analysis weekly** using vault context
5. **📧 Email HTML reports** automatically
6. **📝 Save markdown** to `analysis/` folder
7. **🔄 Auto-update** via GitHub Actions

---

## Next Steps

### Immediate (Do Next):
1. Create `src/analyzers/ai_analyzer.py`
2. Create `src/collectors/ga4_data_collector.py`
3. Create `src/collectors/data_organizer.py`
4. Create `src/generators/report_builder.py`
5. Update `cli.py` with new commands

### Then:
6. Test locally: `python cli.py collect` and `python cli.py analyze`
7. Create GitHub workflows
8. Add `ANTHROPIC_API_KEY` to GitHub secrets
9. Test automation

### Finally:
10. Remove dashboard components
11. Update README
12. Document the new system

---

## Testing the Current State

### Test Funnel Fix:
```bash
python cli.py report daily
# Check reports/daily_report_*.json
# Should show 11 conversions in last 30 days
```

### Test Business Context:
```python
from src.analyzers.business_context import BusinessContextManager

context_mgr = BusinessContextManager()
context = context_mgr.fetch_context()
print(f"Loaded {len(context)} context files")
```

---

## Notes

- All files use absolute imports from `src/`
- Business context fetched fresh each weekly analysis (no stale data)
- Funnel now correctly tracks actual GA4 events
- Conversion rate calculation: total conversions / total sessions
- Date-stamped folders match VOTEGTR-GAds pattern

---

**Last Updated:** 2025-10-21
**Status:** Phase 1 Complete ✅ | Phase 2 In Progress 🚧
