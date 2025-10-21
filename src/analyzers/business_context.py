"""
Business Context Manager
Fetches business context from votegtr-vault repository
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

class BusinessContextManager:
    """Manages business context from votegtr-vault repo"""

    def __init__(self):
        self.vault_repo = 'https://github.com/SPMStrategies/votegtr-vault.git'
        self.context_files = [
            'README.md',
            'target-customer.md',
            'products.md',
            'pricing.md',
            'brand-voice.md',
            'goals.md'
        ]

    def fetch_context(self, use_cache: bool = False) -> Dict[str, str]:
        """
        Fetch latest business context from vault repo

        Args:
            use_cache: If True, use local cache if available (faster)

        Returns:
            Dict of filename -> content
        """
        if use_cache and os.path.exists('context/votegtr-vault'):
            return self._load_from_cache()

        return self._fetch_from_repo()

    def _fetch_from_repo(self) -> Dict[str, str]:
        """Clone repo and extract context files"""
        context = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            print("📥 Fetching business context from votegtr-vault...")

            # Clone vault repo (shallow clone for speed)
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', self.vault_repo, tmpdir],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"⚠️  Warning: Could not fetch vault repo: {result.stderr}")
                return {}

            # Read context files
            for filename in self.context_files:
                filepath = Path(tmpdir) / filename
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        context[filename] = f.read()
                        print(f"  ✓ Loaded {filename}")
                else:
                    print(f"  - {filename} not found, skipping")

            print(f"✅ Loaded {len(context)} context files from vault")

        return context

    def _load_from_cache(self) -> Dict[str, str]:
        """Load context from cached local copy"""
        context = {}
        cache_dir = Path('context/votegtr-vault')

        print("📂 Loading business context from cache...")

        for filename in self.context_files:
            filepath = cache_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    context[filename] = f.read()

        return context

    def format_for_prompt(self, context: Dict[str, str]) -> str:
        """Format context for AI prompt"""
        formatted = "# Business Context (from votegtr-vault repository)\n\n"

        section_titles = {
            'README.md': 'Company Overview',
            'target-customer.md': 'Target Customer Profile',
            'products.md': 'Products & Services',
            'pricing.md': 'Pricing Structure',
            'brand-voice.md': 'Brand Voice & Messaging',
            'goals.md': 'Business Goals'
        }

        for filename, content in context.items():
            title = section_titles.get(filename, filename)
            formatted += f"## {title}\n\n{content}\n\n---\n\n"

        return formatted
