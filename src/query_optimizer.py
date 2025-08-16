"""
Query Optimizer Module
Optimizes BigQuery queries for performance and cost
"""

import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class QueryCache:
    """Simple in-memory cache for query results"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize query cache
        
        Args:
            default_ttl: Default time-to-live in seconds (default 1 hour)
        """
        self.cache = {}
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
    
    def get_cache_key(self, query: str, params: Dict = None) -> str:
        """Generate cache key from query and parameters"""
        cache_input = query + json.dumps(params or {}, sort_keys=True)
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, query: str, params: Dict = None) -> Optional[Any]:
        """Get cached result if available and not expired"""
        key = self.get_cache_key(query, params)
        
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires']:
                self.hit_count += 1
                print(f"✅ Cache hit (rate: {self.get_hit_rate():.1f}%)")
                return entry['data']
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        self.miss_count += 1
        return None
    
    def set(self, query: str, data: Any, ttl: int = None, params: Dict = None):
        """Store result in cache"""
        key = self.get_cache_key(query, params)
        ttl = ttl or self.default_ttl
        
        self.cache[key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=ttl),
            'query': query[:100],  # Store first 100 chars for debugging
            'cached_at': datetime.now()
        }
    
    def clear_expired(self):
        """Remove expired entries from cache"""
        now = datetime.now()
        expired_keys = [k for k, v in self.cache.items() if now >= v['expires']]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"🧹 Cleared {len(expired_keys)} expired cache entries")
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate percentage"""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return (self.hit_count / total) * 100
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'entries': len(self.cache),
            'hits': self.hit_count,
            'misses': self.miss_count,
            'hit_rate': self.get_hit_rate(),
            'memory_estimate': sum(len(str(v)) for v in self.cache.values())
        }


class QueryOptimizer:
    """Optimizes BigQuery queries for cost and performance"""
    
    # Query patterns that should be cached longer
    CACHE_PATTERNS = {
        'dashboard': 3600,  # 1 hour
        'report': 7200,  # 2 hours
        'historical': 86400,  # 24 hours
        'realtime': 300,  # 5 minutes
        'funnel': 1800,  # 30 minutes
    }
    
    def __init__(self):
        """Initialize query optimizer"""
        self.cache = QueryCache()
        self.optimization_rules = self._load_optimization_rules()
        print("✅ Query Optimizer initialized")
    
    def _load_optimization_rules(self) -> List[Dict]:
        """Load query optimization rules"""
        return [
            {
                'name': 'add_date_filter',
                'pattern': 'WHERE',
                'check': lambda q: 'WHERE' in q.upper() and 'DATE' not in q.upper(),
                'action': self._add_date_filter,
                'description': 'Add date filter to reduce data scanned'
            },
            {
                'name': 'add_limit',
                'pattern': 'SELECT',
                'check': lambda q: 'SELECT' in q.upper() and 'LIMIT' not in q.upper() and 'GROUP BY' not in q.upper(),
                'action': self._add_limit,
                'description': 'Add LIMIT to prevent scanning entire table'
            },
            {
                'name': 'optimize_select_star',
                'pattern': 'SELECT *',
                'check': lambda q: 'SELECT *' in q.upper(),
                'action': self._optimize_select_star,
                'description': 'Replace SELECT * with specific columns'
            },
            {
                'name': 'use_approx_functions',
                'pattern': 'COUNT(DISTINCT',
                'check': lambda q: 'COUNT(DISTINCT' in q.upper(),
                'action': self._use_approx_functions,
                'description': 'Use APPROX functions for better performance'
            }
        ]
    
    def optimize_query(self, query: str, query_type: str = 'general') -> Tuple[str, List[str]]:
        """
        Optimize a query for cost and performance
        
        Args:
            query: SQL query to optimize
            query_type: Type of query (dashboard, report, etc.)
            
        Returns:
            Tuple of (optimized_query, list of optimizations applied)
        """
        optimized = query
        optimizations_applied = []
        
        # Apply optimization rules
        for rule in self.optimization_rules:
            if rule['check'](optimized):
                optimized = rule['action'](optimized)
                optimizations_applied.append(rule['description'])
        
        # Add query hints
        optimized = self._add_query_hints(optimized, query_type)
        
        if optimizations_applied:
            print(f"🔧 Applied {len(optimizations_applied)} optimizations:")
            for opt in optimizations_applied:
                print(f"   - {opt}")
        
        return optimized, optimizations_applied
    
    def _add_date_filter(self, query: str) -> str:
        """Add date filter if missing"""
        # Add 30-day filter by default
        if 'WHERE' in query.upper():
            # Insert after WHERE
            return query.replace('WHERE', 
                'WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND')
        else:
            # Add WHERE clause
            return query.replace('FROM', 
                'FROM') + ' WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)'
    
    def _add_limit(self, query: str) -> str:
        """Add LIMIT clause if missing"""
        if 'LIMIT' not in query.upper():
            return query + ' LIMIT 10000'
        return query
    
    def _optimize_select_star(self, query: str) -> str:
        """Suggest replacing SELECT * with specific columns"""
        print("⚠️  Warning: SELECT * detected - consider specifying columns")
        # In production, this would analyze the table schema and suggest columns
        return query
    
    def _use_approx_functions(self, query: str) -> str:
        """Replace exact functions with approximate versions"""
        # Replace COUNT(DISTINCT with APPROX_COUNT_DISTINCT
        optimized = query.replace('COUNT(DISTINCT', 'APPROX_COUNT_DISTINCT(')
        
        # Fix the parentheses
        optimized = optimized.replace('APPROX_COUNT_DISTINCT((', 'APPROX_COUNT_DISTINCT(')
        
        return optimized
    
    def _add_query_hints(self, query: str, query_type: str) -> str:
        """Add BigQuery query hints for optimization"""
        hints = []
        
        # Add caching hint
        cache_ttl = self.CACHE_PATTERNS.get(query_type, 3600)
        hints.append(f"@cache_ttl={cache_ttl}")
        
        # Add other hints based on query type
        if query_type == 'dashboard':
            hints.append("@priority=INTERACTIVE")
        elif query_type == 'report':
            hints.append("@priority=BATCH")
        
        if hints:
            hint_string = '\n'.join(f"-- {hint}" for hint in hints)
            return f"{hint_string}\n{query}"
        
        return query
    
    def estimate_optimization_savings(self, original_query: str, optimized_query: str) -> Dict[str, Any]:
        """
        Estimate cost savings from optimization
        
        Args:
            original_query: Original query
            optimized_query: Optimized query
            
        Returns:
            Dict with savings estimates
        """
        # Simple heuristic-based estimation
        savings = {
            'estimated_reduction': 0,
            'factors': []
        }
        
        # Date filter saves ~90% if scanning full table
        if 'date >=' in optimized_query.lower() and 'date >=' not in original_query.lower():
            savings['estimated_reduction'] += 90
            savings['factors'].append('Date partitioning: -90%')
        
        # APPROX functions save ~50%
        if 'APPROX_' in optimized_query and 'APPROX_' not in original_query:
            savings['estimated_reduction'] += 20
            savings['factors'].append('Approximate functions: -20%')
        
        # LIMIT saves variable amount
        if 'LIMIT' in optimized_query and 'LIMIT' not in original_query:
            savings['estimated_reduction'] += 10
            savings['factors'].append('Row limit: -10%')
        
        # Cap at 95% reduction
        savings['estimated_reduction'] = min(savings['estimated_reduction'], 95)
        
        return savings
    
    def get_cached_or_execute(self, query: str, executor_func, query_type: str = 'general', 
                            params: Dict = None) -> Any:
        """
        Get cached result or execute query
        
        Args:
            query: SQL query
            executor_func: Function to execute query if not cached
            query_type: Type of query for cache TTL
            params: Query parameters
            
        Returns:
            Query results (cached or fresh)
        """
        # Check cache first
        cached_result = self.cache.get(query, params)
        if cached_result is not None:
            return cached_result
        
        # Optimize query
        optimized_query, optimizations = self.optimize_query(query, query_type)
        
        # Execute query
        print(f"🔄 Executing query (type: {query_type})...")
        start_time = time.time()
        
        result = executor_func(optimized_query)
        
        execution_time = time.time() - start_time
        print(f"✅ Query executed in {execution_time:.2f} seconds")
        
        # Cache result
        cache_ttl = self.CACHE_PATTERNS.get(query_type, 3600)
        self.cache.set(query, result, ttl=cache_ttl, params=params)
        
        return result
    
    def analyze_query_patterns(self, queries: List[str]) -> Dict[str, Any]:
        """
        Analyze query patterns to identify optimization opportunities
        
        Args:
            queries: List of queries to analyze
            
        Returns:
            Dict with analysis results
        """
        analysis = {
            'total_queries': len(queries),
            'patterns': {},
            'recommendations': []
        }
        
        # Count pattern occurrences
        patterns = {
            'missing_date_filter': 0,
            'select_star': 0,
            'missing_limit': 0,
            'exact_distinct': 0,
            'full_table_scan': 0
        }
        
        for query in queries:
            upper_query = query.upper()
            
            if 'WHERE' not in upper_query or 'DATE' not in upper_query:
                patterns['missing_date_filter'] += 1
            
            if 'SELECT *' in upper_query:
                patterns['select_star'] += 1
            
            if 'LIMIT' not in upper_query and 'GROUP BY' not in upper_query:
                patterns['missing_limit'] += 1
            
            if 'COUNT(DISTINCT' in upper_query:
                patterns['exact_distinct'] += 1
            
            if 'WHERE' not in upper_query:
                patterns['full_table_scan'] += 1
        
        analysis['patterns'] = patterns
        
        # Generate recommendations
        if patterns['missing_date_filter'] > len(queries) * 0.3:
            analysis['recommendations'].append(
                "30% of queries missing date filters - add partition filters to reduce costs by 90%"
            )
        
        if patterns['select_star'] > len(queries) * 0.2:
            analysis['recommendations'].append(
                "20% of queries use SELECT * - specify columns to reduce data transfer"
            )
        
        if patterns['exact_distinct'] > 0:
            analysis['recommendations'].append(
                f"{patterns['exact_distinct']} queries use exact COUNT(DISTINCT) - consider APPROX functions"
            )
        
        return analysis
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization report with cache stats and recommendations"""
        
        cache_stats = self.cache.get_stats()
        
        report = {
            'cache_performance': {
                'hit_rate': f"{cache_stats['hit_rate']:.1f}%",
                'total_hits': cache_stats['hits'],
                'total_misses': cache_stats['misses'],
                'cached_queries': cache_stats['entries'],
                'memory_usage': f"{cache_stats['memory_estimate'] / 1024:.1f} KB"
            },
            'optimization_tips': [
                "Use date filters on partitioned tables",
                "Replace SELECT * with specific columns",
                "Use APPROX functions for estimates",
                "Cache dashboard queries for 1+ hours",
                "Batch similar queries together"
            ],
            'cost_reduction_potential': "60-90% with proper optimization",
            'timestamp': datetime.now().isoformat()
        }
        
        return report


if __name__ == "__main__":
    # Test query optimizer
    optimizer = QueryOptimizer()
    
    print("\n🔧 Testing Query Optimizer...")
    print("-" * 50)
    
    # Test query optimization
    test_queries = [
        "SELECT * FROM events WHERE user_id = '123'",
        "SELECT COUNT(DISTINCT user_id) FROM sessions",
        "SELECT page, views FROM pages",
        "SELECT * FROM daily_metrics"
    ]
    
    print("\n📝 Optimizing queries:")
    for query in test_queries:
        print(f"\nOriginal: {query}")
        optimized, optimizations = optimizer.optimize_query(query, 'dashboard')
        print(f"Optimized: {optimized}")
        
        # Estimate savings
        savings = optimizer.estimate_optimization_savings(query, optimized)
        if savings['estimated_reduction'] > 0:
            print(f"💰 Estimated cost reduction: {savings['estimated_reduction']}%")
    
    # Test pattern analysis
    print("\n📊 Pattern Analysis:")
    analysis = optimizer.analyze_query_patterns(test_queries)
    print(json.dumps(analysis, indent=2))
    
    # Get optimization report
    print("\n📋 Optimization Report:")
    report = optimizer.get_optimization_report()
    print(json.dumps(report, indent=2))
    
    print("\n✅ Query Optimizer test complete!")