"""
Report Builder
Converts markdown to HTML and manages report storage
"""

import os
from datetime import datetime
from pathlib import Path
import markdown

class ReportBuilder:
    """Builds and saves weekly reports"""

    def __init__(self):
        self.analysis_dir = Path('analysis')
        self.analysis_dir.mkdir(exist_ok=True)
        print("✅ Report Builder initialized")

    def markdown_to_html(self, markdown_text: str, metadata: dict) -> str:
        """
        Convert markdown analysis to HTML email

        Args:
            markdown_text: AI-generated markdown
            metadata: Report metadata (date range, etc.)

        Returns:
            HTML string
        """
        # Convert markdown to HTML
        html_body = markdown.markdown(
            markdown_text,
            extensions=['tables', 'fenced_code', 'nl2br']
        )

        # Wrap in email template
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>VOTEGTR Weekly Analytics - {metadata.get('date_range')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #764ba2;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #764ba2;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background: white;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .metric-box {{
            background: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .highlight {{
            background: #fff3cd;
            padding: 15px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }}
        strong {{
            color: #667eea;
        }}
        ul, ol {{
            padding-left: 25px;
        }}
        li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    <div class="metric-box">
        {html_body}
    </div>
    <footer style="text-align: center; margin-top: 40px; padding: 20px; color: #666; border-top: 1px solid #ddd;">
        <p><strong>VOTEGTR Analytics</strong> | Generated with Claude AI</p>
        <p style="font-size: 0.9em;">Business context from <a href="https://github.com/SPMStrategies/votegtr-vault" style="color: #667eea;">votegtr-vault</a></p>
        <p style="font-size: 0.8em;">Report Period: {metadata.get('date_range')}</p>
    </footer>
</body>
</html>
"""

        return html

    def save_report(self, markdown: str, html: str, date: str):
        """
        Save reports to analysis folder

        Args:
            markdown: Markdown report
            html: HTML report
            date: Report date (YYYY-MM-DD)
        """
        # Save markdown
        md_file = self.analysis_dir / f"{date}-weekly-analysis.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"  ✓ Saved markdown: {md_file}")

        # Save HTML
        html_file = self.analysis_dir / f"{date}-weekly-analysis.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  ✓ Saved HTML: {html_file}")

        return str(md_file), str(html_file)
