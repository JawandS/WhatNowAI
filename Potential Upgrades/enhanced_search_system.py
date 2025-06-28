"""
Enhanced Modular Search System for WhatNowAI
=============================================

This is the core architecture and module structure for the enhanced search system.
Each module is designed to be independent, testable, and production-ready.
"""

# searchmethods/core/__init__.py
"""
Core search functionality and base classes
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import json
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Enumeration of available data sources"""
    WEB_SEARCH = "web_search"
    SOCIAL_MEDIA = "social_media"
    PUBLIC_RECORDS = "public_records"
    NEWS_ARTICLES = "news_articles"
    PROFESSIONAL = "professional"
    ACADEMIC = "academic"
    FORUMS = "forums"
    BLOGS = "blogs"


@dataclass
class SearchResult:
    """Standardized search result structure"""
    source: DataSource
    title: str
    url: str
    content: str
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'source': self.source.value,
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'relevance_score': self.relevance_score,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }
    
    def get_hash(self) -> str:
        """Generate unique hash for deduplication"""
        content = f"{self.source.value}:{self.url}:{self.title}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class UserInterest:
    """Extracted user interest with confidence score"""
    category: str
    keywords: List[str]
    confidence: float
    source: str
    evidence: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'keywords': self.keywords,
            'confidence': self.confidence,
            'source': self.source,
            'evidence': self.evidence
        }


@dataclass
class EnhancedUserProfile:
    """Enhanced user profile with all collected data"""
    # Basic info
    first_name: str
    last_name: str
    full_name: str
    location: Dict[str, Any]
    activity: str
    
    # Extended info
    interests: List[UserInterest] = field(default_factory=list)
    social_profiles: Dict[str, str] = field(default_factory=dict)
    professional_info: Dict[str, Any] = field(default_factory=dict)
    inferred_demographics: Dict[str, Any] = field(default_factory=dict)
    
    # Search metadata
    search_timestamp: datetime = field(default_factory=datetime.now)
    data_sources_used: Set[DataSource] = field(default_factory=set)
    total_results_found: int = 0
    
    def add_interest(self, interest: UserInterest):
        """Add interest with deduplication"""
        for existing in self.interests:
            if existing.category == interest.category and existing.source == interest.source:
                # Update if higher confidence
                if interest.confidence > existing.confidence:
                    existing.keywords.extend(interest.keywords)
                    existing.keywords = list(set(existing.keywords))
                    existing.confidence = interest.confidence
                return
        self.interests.append(interest)
    
    def get_top_interests(self, n: int = 10) -> List[UserInterest]:
        """Get top N interests by confidence"""
        return sorted(self.interests, key=lambda x: x.confidence, reverse=True)[:n]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'basic_info': {
                'first_name': self.first_name,
                'last_name': self.last_name,
                'full_name': self.full_name,
                'location': self.location,
                'activity': self.activity
            },
            'interests': [i.to_dict() for i in self.interests],
            'social_profiles': self.social_profiles,
            'professional_info': self.professional_info,
            'inferred_demographics': self.inferred_demographics,
            'metadata': {
                'search_timestamp': self.search_timestamp.isoformat(),
                'data_sources_used': [ds.value for ds in self.data_sources_used],
                'total_results_found': self.total_results_found
            }
        }


class BaseSearchModule(ABC):
    """Base class for all search modules"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rate_limiter = RateLimiter(
            calls_per_second=self.config.get('rate_limit', 1)
        )
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Perform search and return results"""
        pass
    
    @abstractmethod
    def get_source_type(self) -> DataSource:
        """Return the data source type"""
        pass
    
    async def search_with_rate_limit(self, query: str, **kwargs) -> List[SearchResult]:
        """Search with rate limiting"""
        await self.rate_limiter.acquire()
        return await self.search(query, **kwargs)
    
    def validate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Validate and clean results"""
        valid_results = []
        for result in results:
            if self._is_valid_result(result):
                valid_results.append(result)
        return valid_results
    
    def _is_valid_result(self, result: SearchResult) -> bool:
        """Check if result is valid"""
        return (
            result.title and
            result.url and
            result.content and
            len(result.content) > 50 and
            result.relevance_score >= 0.0
        )


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, calls_per_second: float):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        async with self.lock:
            elapsed = asyncio.get_event_loop().time() - self.last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_call = asyncio.get_event_loop().time()


class SearchOrchestrator:
    """Orchestrates multiple search modules in parallel"""
    
    def __init__(self, modules: List[BaseSearchModule], config: Dict[str, Any] = None):
        self.modules = modules
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.get('max_workers', 10)
        )
    
    async def search_all(self, user_profile: EnhancedUserProfile) -> Dict[str, List[SearchResult]]:
        """Execute all search modules in parallel"""
        self.logger.info(f"Starting orchestrated search for {user_profile.full_name}")
        
        # Prepare search queries
        queries = self._prepare_queries(user_profile)
        
        # Execute searches in parallel
        tasks = []
        for module in self.modules:
            for query in queries:
                task = asyncio.create_task(
                    self._execute_module_search(module, query, user_profile)
                )
                tasks.append((module.get_source_type(), task))
        
        # Collect results
        results = {}
        for source_type, task in tasks:
            try:
                module_results = await task
                if source_type not in results:
                    results[source_type] = []
                results[source_type].extend(module_results)
            except Exception as e:
                self.logger.error(f"Error in {source_type}: {e}")
        
        # Deduplicate results
        for source_type in results:
            results[source_type] = self._deduplicate_results(results[source_type])
        
        return results
    
    def _prepare_queries(self, user_profile: EnhancedUserProfile) -> List[str]:
        """Prepare search queries based on user profile"""
        queries = []
        
        # Name-based queries
        queries.append(f'"{user_profile.full_name}"')
        queries.append(f'"{user_profile.first_name} {user_profile.last_name}"')
        
        # Location-based queries
        if user_profile.location.get('city'):
            queries.append(f'"{user_profile.full_name}" {user_profile.location["city"]}')
        
        # Activity-based queries
        if user_profile.activity:
            queries.append(f'"{user_profile.full_name}" {user_profile.activity}')
        
        # Social media queries
        for platform, handle in user_profile.social_profiles.items():
            if handle:
                queries.append(f'"{handle}" {platform}')
        
        return queries
    
    async def _execute_module_search(
        self, 
        module: BaseSearchModule, 
        query: str, 
        user_profile: EnhancedUserProfile
    ) -> List[SearchResult]:
        """Execute search for a single module"""
        try:
            results = await module.search_with_rate_limit(query)
            validated = module.validate_results(results)
            user_profile.data_sources_used.add(module.get_source_type())
            user_profile.total_results_found += len(validated)
            return validated
        except Exception as e:
            self.logger.error(f"Error in {module.__class__.__name__}: {e}")
            return []
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on hash"""
        seen = set()
        unique = []
        for result in results:
            hash_val = result.get_hash()
            if hash_val not in seen:
                seen.add(hash_val)
                unique.append(result)
        return unique


# searchmethods/core/data_processor.py
"""
Data processing and interest extraction
"""
import re
from typing import List, Dict, Any, Set
import nltk
from collections import Counter
import logging

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except:
    logger.warning("Failed to download NLTK data")


class InterestExtractor:
    """Extract interests from search results"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.interest_categories = self._load_interest_categories()
        self.stop_words = set(nltk.corpus.stopwords.words('english'))
    
    def _load_interest_categories(self) -> Dict[str, List[str]]:
        """Load interest category mappings"""
        return {
            'music': ['concert', 'music', 'band', 'singer', 'album', 'spotify', 'soundcloud', 
                     'guitar', 'piano', 'drums', 'festival', 'dj', 'electronic', 'rock', 'pop', 
                     'jazz', 'classical', 'hip-hop', 'rap'],
            'sports': ['sports', 'football', 'basketball', 'baseball', 'soccer', 'tennis', 
                      'golf', 'running', 'fitness', 'gym', 'workout', 'athlete', 'team', 
                      'game', 'match', 'tournament', 'league'],
            'technology': ['tech', 'programming', 'coding', 'software', 'developer', 'engineer',
                          'computer', 'ai', 'machine learning', 'data science', 'startup',
                          'app', 'website', 'github', 'code', 'hackathon'],
            'arts': ['art', 'painting', 'drawing', 'sculpture', 'gallery', 'museum', 'artist',
                    'creative', 'design', 'photography', 'photo', 'instagram', 'visual'],
            'food': ['food', 'restaurant', 'cooking', 'chef', 'recipe', 'cuisine', 'dining',
                    'foodie', 'eat', 'taste', 'meal', 'dish', 'culinary'],
            'travel': ['travel', 'trip', 'vacation', 'tourism', 'flight', 'hotel', 'destination',
                      'adventure', 'explore', 'journey', 'abroad', 'passport'],
            'fitness': ['fitness', 'health', 'exercise', 'yoga', 'pilates', 'crossfit', 'marathon',
                       'cycling', 'swimming', 'training', 'wellness', 'nutrition'],
            'gaming': ['gaming', 'game', 'gamer', 'xbox', 'playstation', 'nintendo', 'steam',
                      'twitch', 'esports', 'multiplayer', 'rpg', 'fps'],
            'education': ['education', 'learning', 'course', 'university', 'college', 'degree',
                         'student', 'teacher', 'academic', 'research', 'study', 'school'],
            'business': ['business', 'entrepreneur', 'startup', 'company', 'ceo', 'founder',
                        'marketing', 'sales', 'finance', 'investment', 'linkedin'],
            'entertainment': ['movie', 'film', 'tv', 'show', 'netflix', 'theater', 'cinema',
                             'actor', 'actress', 'director', 'series', 'streaming'],
            'fashion': ['fashion', 'style', 'clothing', 'outfit', 'brand', 'designer', 'trend',
                       'wardrobe', 'accessories', 'shoes', 'jewelry'],
            'nature': ['nature', 'outdoor', 'hiking', 'camping', 'mountain', 'beach', 'forest',
                      'park', 'wildlife', 'environment', 'eco', 'green'],
            'social': ['community', 'volunteer', 'charity', 'nonprofit', 'social', 'cause',
                      'helping', 'support', 'organization', 'impact'],
            'culture': ['culture', 'history', 'heritage', 'tradition', 'language', 'cultural',
                       'festival', 'celebration', 'customs', 'diversity']
        }
    
    def extract_interests(self, search_results: List[SearchResult]) -> List[UserInterest]:
        """Extract interests from search results"""
        interests = []
        
        # Combine all text content
        all_text = ' '.join([
            f"{result.title} {result.content}" 
            for result in search_results
        ])
        
        # Extract keywords
        keywords = self._extract_keywords(all_text)
        
        # Categorize interests
        category_scores = self._categorize_keywords(keywords)
        
        # Create UserInterest objects
        for category, score in category_scores.items():
            if score > self.config.get('min_interest_score', 0.3):
                interest = UserInterest(
                    category=category,
                    keywords=self._get_category_keywords(keywords, category),
                    confidence=min(score, 1.0),
                    source='content_analysis',
                    evidence=f"Found {int(score * 100)} references to {category}-related content"
                )
                interests.append(interest)
        
        return interests
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Tokenize and clean
        tokens = nltk.word_tokenize(text.lower())
        
        # Remove stopwords and short words
        keywords = [
            token for token in tokens
            if token not in self.stop_words
            and len(token) > 3
            and token.isalpha()
        ]
        
        # Get POS tags and filter
        pos_tags = nltk.pos_tag(keywords)
        
        # Keep nouns and verbs
        filtered_keywords = [
            word for word, pos in pos_tags
            if pos.startswith('NN') or pos.startswith('VB')
        ]
        
        return filtered_keywords
    
    def _categorize_keywords(self, keywords: List[str]) -> Dict[str, float]:
        """Categorize keywords into interest categories"""
        keyword_freq = Counter(keywords)
        category_scores = {}
        
        for category, category_keywords in self.interest_categories.items():
            score = 0
            matches = 0
            
            for keyword, freq in keyword_freq.items():
                if any(cat_kw in keyword for cat_kw in category_keywords):
                    score += freq
                    matches += 1
            
            if matches > 0:
                # Normalize score
                category_scores[category] = score / (len(keywords) + 1)
        
        return category_scores
    
    def _get_category_keywords(self, keywords: List[str], category: str) -> List[str]:
        """Get keywords that match a category"""
        category_keywords = self.interest_categories.get(category, [])
        matching = []
        
        for keyword in set(keywords):
            if any(cat_kw in keyword for cat_kw in category_keywords):
                matching.append(keyword)
        
        return matching[:10]  # Top 10 keywords


class DataFilter:
    """Filter and validate search results"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.min_relevance = config.get('min_relevance_score', 0.5)
    
    def filter_results(
        self, 
        results: List[SearchResult], 
        user_profile: EnhancedUserProfile
    ) -> List[SearchResult]:
        """Filter results based on relevance to user"""
        filtered = []
        
        for result in results:
            if self._is_relevant(result, user_profile):
                filtered.append(result)
        
        # Sort by relevance
        return sorted(filtered, key=lambda x: x.relevance_score, reverse=True)
    
    def _is_relevant(self, result: SearchResult, user_profile: EnhancedUserProfile) -> bool:
        """Check if result is relevant to user"""
        # Check minimum relevance score
        if result.relevance_score < self.min_relevance:
            return False
        
        # Check name match
        if not self._contains_name(result, user_profile):
            return False
        
        # Check location relevance if available
        if user_profile.location.get('city'):
            if not self._is_location_relevant(result, user_profile):
                result.relevance_score *= 0.8  # Reduce score for non-local
        
        return True
    
    def _contains_name(self, result: SearchResult, user_profile: EnhancedUserProfile) -> bool:
        """Check if result contains user's name"""
        text = f"{result.title} {result.content}".lower()
        
        # Check full name
        if user_profile.full_name.lower() in text:
            return True
        
        # Check partial name
        if (user_profile.first_name.lower() in text and 
            user_profile.last_name.lower() in text):
            return True
        
        # Check social handles
        for handle in user_profile.social_profiles.values():
            if handle and handle.lower() in text:
                return True
        
        return False
    
    def _is_location_relevant(self, result: SearchResult, user_profile: EnhancedUserProfile) -> bool:
        """Check if result is location relevant"""
        text = f"{result.title} {result.content}".lower()
        
        city = user_profile.location.get('city', '').lower()
        state = user_profile.location.get('state', '').lower()
        country = user_profile.location.get('country', '').lower()
        
        return any(loc in text for loc in [city, state, country] if loc)
