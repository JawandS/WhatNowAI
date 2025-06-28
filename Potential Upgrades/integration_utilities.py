# searchmethods/utils/cache_manager.py
"""
Caching utilities for search results
"""
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis
import pickle
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage caching of search results"""
    
    def __init__(self, cache_type: str = "file", config: Dict[str, Any] = None):
        """
        Initialize cache manager
        
        Args:
            cache_type: "file", "redis", or "memory"
            config: Cache configuration
        """
        self.cache_type = cache_type
        self.config = config or {}
        self.cache_dir = self.config.get('cache_dir', 'cache/search_results')
        self.ttl = self.config.get('ttl_hours', 24)
        
        if cache_type == "file":
            os.makedirs(self.cache_dir, exist_ok=True)
            self.cache = {}
        elif cache_type == "redis":
            self.redis_client = redis.Redis(
                host=self.config.get('redis_host', 'localhost'),
                port=self.config.get('redis_port', 6379),
                db=self.config.get('redis_db', 0)
            )
        elif cache_type == "memory":
            self.cache = {}
    
    def _generate_key(self, user_profile: Dict[str, Any]) -> str:
        """Generate cache key from user profile"""
        key_data = {
            'name': user_profile.get('full_name', ''),
            'location': user_profile.get('location', {}).get('city', ''),
            'activity': user_profile.get('activity', '')
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached results"""
        key = self._generate_key(user_profile)
        
        try:
            if self.cache_type == "file":
                cache_file = os.path.join(self.cache_dir, f"{key}.json")
                if os.path.exists(cache_file):
                    # Check age
                    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
                    if file_age < timedelta(hours=self.ttl):
                        with open(cache_file, 'r') as f:
                            return json.load(f)
                            
            elif self.cache_type == "redis":
                data = self.redis_client.get(key)
                if data:
                    return pickle.loads(data)
                    
            elif self.cache_type == "memory":
                if key in self.cache:
                    data, timestamp = self.cache[key]
                    if datetime.now() - timestamp < timedelta(hours=self.ttl):
                        return data
                        
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            
        return None
    
    def set(self, user_profile: Dict[str, Any], results: Dict[str, Any]):
        """Set cache results"""
        key = self._generate_key(user_profile)
        
        try:
            if self.cache_type == "file":
                cache_file = os.path.join(self.cache_dir, f"{key}.json")
                with open(cache_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                    
            elif self.cache_type == "redis":
                self.redis_client.setex(
                    key,
                    timedelta(hours=self.ttl),
                    pickle.dumps(results)
                )
                
            elif self.cache_type == "memory":
                self.cache[key] = (results, datetime.now())
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def clear(self):
        """Clear all cache"""
        try:
            if self.cache_type == "file":
                for file in os.listdir(self.cache_dir):
                    if file.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, file))
                        
            elif self.cache_type == "redis":
                self.redis_client.flushdb()
                
            elif self.cache_type == "memory":
                self.cache.clear()
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


# searchmethods/utils/privacy_filter.py
"""
Privacy and content filtering utilities
"""
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PrivacyFilter:
    """Filter sensitive information from search results"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.sensitive_patterns = self._load_sensitive_patterns()
    
    def _load_sensitive_patterns(self) -> Dict[str, re.Pattern]:
        """Load patterns for sensitive information"""
        return {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'address': re.compile(r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Plaza|Pl)\b', re.IGNORECASE),
            'date_of_birth': re.compile(r'\b(?:DOB|Date of Birth|Born)[\s:]+\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', re.IGNORECASE)
        }
    
    def filter_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter sensitive information from results"""
        filtered = []
        
        for result in results:
            # Create a copy to avoid modifying original
            filtered_result = result.copy()
            
            # Filter content
            if 'content' in filtered_result:
                filtered_result['content'] = self._filter_text(filtered_result['content'])
            
            # Filter title
            if 'title' in filtered_result:
                filtered_result['title'] = self._filter_text(filtered_result['title'])
            
            filtered.append(filtered_result)
        
        return filtered
    
    def _filter_text(self, text: str) -> str:
        """Filter sensitive information from text"""
        if not text:
            return text
        
        filtered_text = text
        
        for pattern_name, pattern in self.sensitive_patterns.items():
            if pattern_name == 'email' and self.config.get('preserve_emails', False):
                # Partially mask emails
                filtered_text = pattern.sub(self._mask_email, filtered_text)
            else:
                # Replace with generic marker
                filtered_text = pattern.sub(f'[{pattern_name.upper()}_REDACTED]', filtered_text)
        
        return filtered_text
    
    def _mask_email(self, match):
        """Partially mask email addresses"""
        email = match.group(0)
        parts = email.split('@')
        if len(parts) == 2:
            username = parts[0]
            if len(username) > 3:
                masked = username[:2] + '*' * (len(username) - 3) + username[-1]
                return f"{masked}@{parts[1]}"
        return '[EMAIL_REDACTED]'


# searchmethods/utils/rate_monitor.py
"""
API rate limit monitoring and management
"""
import time
from collections import defaultdict
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RateMonitor:
    """Monitor and manage API rate limits"""
    
    def __init__(self):
        self.api_calls = defaultdict(list)
        self.rate_limits = {
            'google': {'calls': 100, 'window': 3600},  # 100 calls per hour
            'github': {'calls': 60, 'window': 3600},   # 60 calls per hour
            'eventbrite': {'calls': 1000, 'window': 3600},  # 1000 calls per hour
            'openai': {'calls': 60, 'window': 60},     # 60 calls per minute
        }
    
    def check_rate_limit(self, api_name: str) -> bool:
        """Check if API call is within rate limit"""
        if api_name not in self.rate_limits:
            return True
        
        current_time = time.time()
        window = self.rate_limits[api_name]['window']
        max_calls = self.rate_limits[api_name]['calls']
        
        # Remove old calls outside window
        self.api_calls[api_name] = [
            call_time for call_time in self.api_calls[api_name]
            if current_time - call_time < window
        ]
        
        # Check if under limit
        return len(self.api_calls[api_name]) < max_calls
    
    def record_call(self, api_name: str):
        """Record an API call"""
        self.api_calls[api_name].append(time.time())
    
    def get_wait_time(self, api_name: str) -> float:
        """Get time to wait before next call"""
        if api_name not in self.rate_limits:
            return 0
        
        if self.check_rate_limit(api_name):
            return 0
        
        current_time = time.time()
        window = self.rate_limits[api_name]['window']
        
        # Find oldest call in window
        oldest_call = min(self.api_calls[api_name])
        wait_time = window - (current_time - oldest_call)
        
        return max(0, wait_time)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        stats = {}
        current_time = time.time()
        
        for api_name, limits in self.rate_limits.items():
            window = limits['window']
            max_calls = limits['calls']
            
            # Count recent calls
            recent_calls = [
                call_time for call_time in self.api_calls[api_name]
                if current_time - call_time < window
            ]
            
            stats[api_name] = {
                'used': len(recent_calls),
                'limit': max_calls,
                'percentage': (len(recent_calls) / max_calls * 100) if max_calls > 0 else 0,
                'window_seconds': window
            }
        
        return stats


# Complete integration guide
COMPLETE_INTEGRATION_GUIDE = """
# WhatNowAI Enhanced Search Integration Guide

## Overview
This guide provides complete instructions for integrating the enhanced search system into your WhatNowAI application.

## Directory Structure
```
whatnowai/
├── searchmethods/
│   ├── core/
│   │   ├── __init__.py
│   │   └── data_processor.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   └── web_scrapers.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── ai_processor.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cache_manager.py
│   │   ├── privacy_filter.py
│   │   └── rate_monitor.py
│   ├── __init__.py
│   ├── background_search.py (original)
│   └── enhanced_search.py (new)
├── services/
│   ├── eventbrite_service.py (new)
│   └── ... (existing services)
├── config/
│   └── settings.py (update)
└── requirements.txt (update)
```

## Step-by-Step Integration

### 1. Update requirements.txt
```txt
# Core dependencies
aiohttp>=3.8.0
beautifulsoup4>=4.11.0
requests>=2.28.0
python-dateutil>=2.8.0

# Web scraping
selenium>=4.0.0
cloudscraper>=1.2.0
fake-useragent>=1.4.0

# NLP and ML
nltk>=3.8.0
scikit-learn>=1.3.0
numpy>=1.24.0

# AI (optional)
openai>=1.0.0
transformers>=4.35.0
sentence-transformers>=2.2.0
torch>=2.0.0

# Caching (optional)
redis>=4.5.0

# Utilities
python-dotenv>=1.0.0
```

### 2. Update config/settings.py
```python
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
EVENTBRITE_API_KEY = os.getenv('EVENTBRITE_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

# Enhanced Search Configuration
SEARCH_CONFIG = {
    'scrapers': {
        'use_selenium': False,
        'rate_limit': 1,
        'timeout': 30,
        'max_retries': 3
    },
    'orchestrator': {
        'max_workers': 10,
        'timeout': 60
    },
    'interest_extraction': {
        'min_interest_score': 0.3,
        'max_keywords_per_interest': 10
    },
    'data_filtering': {
        'min_relevance_score': 0.5,
        'preserve_emails': False
    },
    'cache': {
        'type': 'file',  # 'file', 'redis', or 'memory'
        'ttl_hours': 24,
        'cache_dir': 'cache/search_results'
    }
}

# AI Configuration
AI_CONFIG = {
    'openai_model': 'gpt-3.5-turbo',
    'use_huggingface': True,
    'hf_model': 'facebook/bart-large-mnli',
    'use_local_embeddings': True,
    'embedding_model': 'all-MiniLM-L6-v2'
}

# Eventbrite Configuration
EVENTBRITE_CONFIG = {
    'MAX_EVENTS': 30,
    'BASE_URL': 'https://www.eventbriteapi.com/v3',
    'TIMEOUT': 10,
    'DEFAULT_RADIUS_MILES': 50,
    'DEFAULT_TIME_RANGE_HOURS': 12
}
```

### 3. Update routes.py
```python
from searchmethods.enhanced_search import perform_enhanced_background_search
from searchmethods.utils.cache_manager import CacheManager
from searchmethods.utils.privacy_filter import PrivacyFilter

# Initialize utilities
cache_manager = CacheManager(
    cache_type=app.config.get('SEARCH_CONFIG', {}).get('cache', {}).get('type', 'file')
)
privacy_filter = PrivacyFilter()

@main_bp.route('/process', methods=['POST'])
def process_request():
    try:
        data = request.get_json()
        
        # Check cache first
        cached_result = cache_manager.get(data)
        if cached_result:
            logger.info("Returning cached results")
            return jsonify(cached_result)
        
        # Prepare user data
        user_data = {
            'name': f"{data.get('name', '')}",
            'location': data.get('location', {}),
            'latitude': data['location'].get('latitude'),
            'longitude': data['location'].get('longitude'),
            'activity': data.get('activity', ''),
            'social_handles': data.get('social', {})
        }
        
        # Run enhanced search
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            search_result = loop.run_until_complete(
                perform_enhanced_background_search(user_data)
            )
        finally:
            loop.close()
        
        # Filter sensitive information
        if search_result.get('search_results'):
            for source, results in search_result['search_results'].items():
                if 'top_results' in results:
                    results['top_results'] = privacy_filter.filter_results(
                        results['top_results']
                    )
        
        # Cache results
        cache_manager.set(data, search_result)
        
        # Prepare response
        response = {
            'success': search_result.get('success', False),
            'name': data.get('name'),
            'activity': data.get('activity'),
            'location': data.get('location'),
            'interests': search_result.get('interests', []),
            'events': search_result.get('events', []),
            'search_summaries': {
                'general': f"Found {search_result['metadata']['total_results_found']} results",
                'interests': f"Discovered {len(search_result.get('interests', []))} interests",
                'events': f"Found {len(search_result.get('events', []))} nearby events"
            },
            'redirect_to_map': True,
            'map_url': '/map'
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in process_request: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500
```

### 4. Update map integration
```python
# In services/mapping_service.py, add:

def add_eventbrite_events(self, events: List[Dict[str, Any]]):
    """Add Eventbrite events to the map"""
    for event in events:
        try:
            marker = MapMarker(
                id=f"eb_{event['id']}",
                name=event['name'],
                latitude=event['latitude'],
                longitude=event['longitude'],
                category=event['category'],
                subcategory=event.get('subcategory', ''),
                description=event.get('description', ''),
                url=event['url'],
                date=event['start_time'].split('T')[0],
                time=event['start_time'].split('T')[1][:5],
                venue=event['venue_name'],
                address=event['venue_address'],
                price_min=event.get('price_min'),
                price_max=event.get('price_max'),
                image_url=event.get('image_url', ''),
                source="eventbrite"
            )
            self.markers.append(marker)
        except Exception as e:
            logger.warning(f"Failed to add Eventbrite event: {e}")
```

### 5. Create monitoring dashboard
```python
# monitoring/dashboard.py
from flask import Blueprint, render_template, jsonify
from searchmethods.utils.rate_monitor import RateMonitor

monitoring_bp = Blueprint('monitoring', __name__)
rate_monitor = RateMonitor()

@monitoring_bp.route('/monitoring/dashboard')
def dashboard():
    return render_template('monitoring/dashboard.html')

@monitoring_bp.route('/monitoring/api/stats')
def api_stats():
    stats = rate_monitor.get_usage_stats()
    return jsonify(stats)
```

### 6. Privacy and compliance
```python
# Add to your terms of service and privacy policy:
- Data collection disclosure
- Third-party API usage
- Data retention policies
- User consent mechanisms
```

### 7. Performance optimizations
```python
# Add to config:
PERFORMANCE_CONFIG = {
    'enable_caching': True,
    'cache_ttl_hours': 24,
    'max_concurrent_searches': 10,
    'request_timeout': 30,
    'enable_result_pagination': True,
    'results_per_page': 20
}
```

### 8. Error handling and logging
```python
# Update logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/enhanced_search.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        'searchmethods': {
            'handlers': ['file'],
            'level': 'INFO'
        }
    }
}
```

## Testing

### Unit tests
```python
# tests/test_enhanced_search.py
import pytest
import asyncio
from searchmethods.enhanced_search import EnhancedSearchSystem

@pytest.mark.asyncio
async def test_search_system():
    system = EnhancedSearchSystem()
    
    result = await system.perform_enhanced_search(
        first_name="Test",
        last_name="User",
        location={'city': 'San Francisco', 'latitude': 37.7749, 'longitude': -122.4194},
        activity="test activity"
    )
    
    assert result['success'] == True
    assert 'interests' in result
    assert 'events' in result
    
    await system.cleanup()
```

## Deployment

### Environment setup
```bash
# .env file
FLASK_ENV=production
OPENAI_API_KEY=your-key
EVENTBRITE_API_KEY=your-key
REDIS_URL=redis://localhost:6379/0
```

### Docker support
```dockerfile
# Dockerfile additions
RUN apt-get update && apt-get install -y \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
```

## Monitoring and maintenance

1. Monitor API usage through dashboard
2. Review logs for errors
3. Update search patterns based on results
4. Refresh API keys as needed
5. Clear cache periodically

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review rate limit status
3. Verify API keys are valid
4. Test individual components
"""

# Save complete guide
with open('COMPLETE_INTEGRATION_GUIDE.md', 'w') as f:
    f.write(COMPLETE_INTEGRATION_GUIDE)
    
print("Complete integration guide saved to COMPLETE_INTEGRATION_GUIDE.md")
