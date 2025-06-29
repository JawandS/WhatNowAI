"""
Enhanced Background Search Service with Advanced Personalization Data Extraction

This module provides a comprehensive search system that extracts detailed user insights
for better personalization of event recommendations.
"""

import asyncio
import aiohttp
import logging
import json
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PersonalizationInsight:
    """Structured insight for personalization"""
    category: str
    keywords: List[str]
    confidence: float
    evidence: str
    source: str
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'keywords': self.keywords,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'source': self.source,
            'context': self.context
        }


@dataclass
class EnhancedUserProfile:
    """Enhanced user profile with detailed personalization data"""
    name: str
    location: str = ""
    social_handles: Dict[str, str] = field(default_factory=dict)
    activity: str = ""
    
    # Enhanced personalization data
    interests: List[PersonalizationInsight] = field(default_factory=list)
    behavioral_patterns: Dict[str, float] = field(default_factory=dict)
    activity_preferences: Dict[str, Any] = field(default_factory=dict)
    social_context: Dict[str, Any] = field(default_factory=dict)
    location_insights: Dict[str, Any] = field(default_factory=dict)
    
    def add_insight(self, insight: PersonalizationInsight):
        """Add personalization insight with deduplication"""
        for existing in self.interests:
            if existing.category == insight.category and existing.source == insight.source:
                # Merge insights
                existing.keywords.extend(insight.keywords)
                existing.keywords = list(set(existing.keywords))
                existing.confidence = max(existing.confidence, insight.confidence)
                return
        self.interests.append(insight)
    
    def get_top_interests(self, n: int = 10) -> List[PersonalizationInsight]:
        """Get top N interests by confidence"""
        return sorted(self.interests, key=lambda x: x.confidence, reverse=True)[:n]


class AdvancedInterestExtractor:
    """Advanced interest extraction with NLP and context analysis"""
    
    def __init__(self):
        self.interest_taxonomy = self._load_comprehensive_taxonomy()
        self.behavioral_indicators = self._load_behavioral_indicators()
        self.activity_contexts = self._load_activity_contexts()
    
    def _load_comprehensive_taxonomy(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive interest taxonomy"""
        return {
            'music': {
                'keywords': [
                    'music', 'concert', 'festival', 'band', 'artist', 'album', 'song', 'lyrics',
                    'guitar', 'piano', 'drums', 'violin', 'bass', 'synthesizer', 'dj',
                    'jazz', 'rock', 'pop', 'classical', 'hip-hop', 'rap', 'electronic', 'edm',
                    'country', 'blues', 'reggae', 'folk', 'indie', 'metal', 'punk', 'r&b',
                    'spotify', 'soundcloud', 'apple music', 'vinyl', 'live music', 'symphony',
                    'opera', 'karaoke', 'open mic', 'jam session', 'recording', 'studio'
                ],
                'venues': ['concert hall', 'club', 'stadium', 'amphitheater', 'bar', 'festival grounds'],
                'activities': ['listening', 'playing', 'composing', 'producing', 'performing', 'singing'],
                'skill_levels': ['beginner', 'intermediate', 'advanced', 'professional'],
                'engagement_patterns': ['daily listener', 'weekend warrior', 'concert goer', 'musician']
            },
            'sports': {
                'keywords': [
                    'sports', 'football', 'basketball', 'baseball', 'soccer', 'tennis', 'golf',
                    'hockey', 'swimming', 'running', 'cycling', 'fitness', 'gym', 'workout',
                    'marathon', 'triathlon', 'yoga', 'pilates', 'crossfit', 'weightlifting',
                    'volleyball', 'softball', 'wrestling', 'boxing', 'mma', 'skiing', 'snowboarding',
                    'surfing', 'climbing', 'hiking', 'camping', 'fishing', 'hunting', 'athletics',
                    'training', 'coach', 'team', 'league', 'tournament', 'competition'
                ],
                'venues': ['stadium', 'gym', 'court', 'field', 'track', 'pool', 'mountain', 'beach'],
                'activities': ['playing', 'watching', 'training', 'coaching', 'competing'],
                'skill_levels': ['recreational', 'amateur', 'semi-pro', 'professional'],
                'engagement_patterns': ['weekend athlete', 'daily trainer', 'seasonal player', 'spectator']
            },
            'technology': {
                'keywords': [
                    'technology', 'programming', 'coding', 'software', 'developer', 'engineer',
                    'computer', 'ai', 'machine learning', 'data science', 'startup', 'app',
                    'website', 'github', 'python', 'javascript', 'java', 'c++', 'react', 'node',
                    'blockchain', 'crypto', 'bitcoin', 'ethereum', 'iot', 'robotics', 'vr', 'ar',
                    'gaming', 'hackathon', 'open source', 'cloud', 'aws', 'google cloud', 'azure'
                ],
                'venues': ['office', 'coworking', 'hackathon', 'conference', 'meetup', 'lab'],
                'activities': ['developing', 'coding', 'building', 'designing', 'testing', 'learning'],
                'skill_levels': ['beginner', 'intermediate', 'senior', 'expert', 'architect'],
                'engagement_patterns': ['hobbyist', 'professional', 'entrepreneur', 'student']
            },
            'arts': {
                'keywords': [
                    'art', 'painting', 'drawing', 'sculpture', 'photography', 'gallery', 'museum',
                    'exhibition', 'artist', 'creative', 'design', 'theater', 'drama', 'acting',
                    'dance', 'ballet', 'contemporary', 'crafts', 'pottery', 'jewelry', 'fashion',
                    'illustration', 'digital art', 'graphic design', 'animation', 'film', 'video',
                    'writing', 'poetry', 'literature', 'storytelling', 'creative writing'
                ],
                'venues': ['gallery', 'museum', 'theater', 'studio', 'workshop', 'exhibition hall'],
                'activities': ['creating', 'exhibiting', 'performing', 'designing', 'collecting', 'viewing'],
                'skill_levels': ['amateur', 'hobbyist', 'semi-professional', 'professional'],
                'engagement_patterns': ['creator', 'collector', 'appreciator', 'performer']
            },
            'food': {
                'keywords': [
                    'food', 'cooking', 'baking', 'cuisine', 'restaurant', 'chef', 'recipe',
                    'culinary', 'dining', 'foodie', 'wine', 'beer', 'coffee', 'tea', 'cocktails',
                    'organic', 'vegan', 'vegetarian', 'nutrition', 'gourmet', 'street food',
                    'fine dining', 'barbecue', 'grilling', 'dessert', 'pastry', 'bread', 'pasta',
                    'sushi', 'pizza', 'burger', 'tasting', 'food truck', 'farmers market'
                ],
                'venues': ['restaurant', 'kitchen', 'market', 'festival', 'tasting room', 'brewery'],
                'activities': ['cooking', 'baking', 'tasting', 'reviewing', 'exploring', 'dining'],
                'skill_levels': ['beginner', 'home cook', 'enthusiast', 'professional'],
                'engagement_patterns': ['home chef', 'restaurant explorer', 'food critic', 'social diner']
            },
            'travel': {
                'keywords': [
                    'travel', 'tourism', 'vacation', 'trip', 'adventure', 'backpacking', 'hotel',
                    'flight', 'destination', 'explore', 'culture', 'sightseeing', 'beach',
                    'mountain', 'city', 'country', 'international', 'domestic', 'cruise',
                    'road trip', 'camping', 'hiking', 'photography', 'solo travel', 'group travel',
                    'budget travel', 'luxury travel', 'business travel', 'wanderlust'
                ],
                'venues': ['destinations', 'hotels', 'airports', 'attractions', 'tours', 'hostels'],
                'activities': ['visiting', 'exploring', 'photographing', 'blogging', 'planning'],
                'skill_levels': ['novice', 'experienced', 'expert', 'travel hacker'],
                'engagement_patterns': ['occasional traveler', 'frequent flyer', 'digital nomad', 'explorer']
            },
            'fitness': {
                'keywords': [
                    'fitness', 'health', 'exercise', 'workout', 'gym', 'training', 'cardio',
                    'strength', 'endurance', 'flexibility', 'yoga', 'pilates', 'crossfit',
                    'running', 'jogging', 'cycling', 'swimming', 'weightlifting', 'bodybuilding',
                    'nutrition', 'diet', 'wellness', 'mindfulness', 'meditation', 'recovery'
                ],
                'venues': ['gym', 'studio', 'park', 'track', 'pool', 'home', 'outdoor'],
                'activities': ['exercising', 'training', 'practicing', 'competing', 'teaching'],
                'skill_levels': ['beginner', 'intermediate', 'advanced', 'trainer'],
                'engagement_patterns': ['casual exerciser', 'fitness enthusiast', 'athlete', 'trainer']
            },
            'learning': {
                'keywords': [
                    'education', 'learning', 'course', 'class', 'workshop', 'seminar', 'training',
                    'skill', 'knowledge', 'study', 'research', 'university', 'college', 'school',
                    'online learning', 'mooc', 'certification', 'degree', 'tutorial', 'book',
                    'podcast', 'documentary', 'lecture', 'conference', 'self-improvement'
                ],
                'venues': ['classroom', 'library', 'online', 'conference center', 'workshop space'],
                'activities': ['studying', 'researching', 'practicing', 'teaching', 'discussing'],
                'skill_levels': ['student', 'intermediate', 'advanced', 'expert'],
                'engagement_patterns': ['lifelong learner', 'skill builder', 'knowledge seeker', 'educator']
            }
        }
    
    def _load_behavioral_indicators(self) -> Dict[str, List[str]]:
        """Load behavioral pattern indicators"""
        return {
            'high_engagement': [
                'passionate', 'obsessed', 'love', 'dedicated', 'committed', 'serious',
                'professional', 'expert', 'years of experience', 'certified', 'advanced',
                'compete', 'perform', 'teach', 'mentor', 'lead', 'organize'
            ],
            'social_preference': [
                'group', 'team', 'community', 'together', 'friends', 'social', 'club',
                'meetup', 'class', 'workshop', 'collaborative', 'networking'
            ],
            'solo_preference': [
                'alone', 'individual', 'personal', 'solo', 'private', 'independent',
                'self-directed', 'meditation', 'reading', 'writing', 'reflection'
            ],
            'adventure_seeking': [
                'adventure', 'extreme', 'adrenaline', 'challenge', 'risk', 'new',
                'explore', 'discover', 'unknown', 'exciting', 'thrill', 'daring'
            ],
            'learning_oriented': [
                'learn', 'study', 'education', 'knowledge', 'skill', 'improve',
                'develop', 'grow', 'understand', 'research', 'curious', 'explore'
            ],
            'creative_expression': [
                'create', 'make', 'build', 'design', 'artistic', 'original',
                'unique', 'innovative', 'express', 'imagination', 'creative'
            ],
            'health_conscious': [
                'healthy', 'wellness', 'fitness', 'nutrition', 'organic', 'natural',
                'exercise', 'mindful', 'balance', 'wellbeing', 'self-care'
            ],
            'time_patterns': {
                'morning': ['morning', 'early', 'dawn', 'sunrise', 'am', 'breakfast'],
                'evening': ['evening', 'night', 'sunset', 'pm', 'late', 'dinner'],
                'weekend': ['weekend', 'saturday', 'sunday', 'days off', 'leisure'],
                'weekday': ['weekday', 'workday', 'monday', 'friday', 'business hours']
            }
        }
    
    def _load_activity_contexts(self) -> Dict[str, List[str]]:
        """Load activity context indicators"""
        return {
            'urgency': {
                'immediate': ['now', 'today', 'tonight', 'asap', 'urgent', 'immediate'],
                'soon': ['soon', 'this week', 'weekend', 'next few days'],
                'flexible': ['sometime', 'eventually', 'when possible', 'no rush']
            },
            'budget': {
                'free': ['free', 'no cost', 'budget', 'cheap', 'affordable'],
                'moderate': ['reasonable', 'moderate', 'fair price', 'worth it'],
                'premium': ['premium', 'high-end', 'luxury', 'expensive', 'investment']
            },
            'experience_level': {
                'beginner': ['beginner', 'new', 'first time', 'never done', 'learning'],
                'intermediate': ['some experience', 'intermediate', 'familiar', 'practiced'],
                'advanced': ['experienced', 'advanced', 'expert', 'professional', 'skilled']
            }
        }
    
    def extract_insights(self, text: str, source: str, context: str = "") -> List[PersonalizationInsight]:
        """Extract personalization insights from text"""
        if not text:
            return []
        
        text_lower = text.lower()
        insights = []
        
        # Extract interest-based insights
        for category, category_data in self.interest_taxonomy.items():
            keyword_matches = self._find_keyword_matches(text_lower, category_data['keywords'])
            
            if keyword_matches:
                confidence = self._calculate_confidence(text_lower, keyword_matches, category_data)
                
                if confidence > 0.2:  # Minimum confidence threshold
                    evidence = self._extract_evidence(text, keyword_matches)
                    
                    insight = PersonalizationInsight(
                        category=category,
                        keywords=keyword_matches,
                        confidence=confidence,
                        evidence=evidence,
                        source=source,
                        context=context
                    )
                    insights.append(insight)
        
        return insights
    
    def _find_keyword_matches(self, text: str, keywords: List[str]) -> List[str]:
        """Find keyword matches in text"""
        matches = []
        for keyword in keywords:
            if keyword in text:
                matches.append(keyword)
        return matches
    
    def _calculate_confidence(self, text: str, matches: List[str], category_data: Dict) -> float:
        """Calculate confidence score for interest category"""
        base_confidence = len(matches) / len(category_data['keywords'])
        
        # Boost for engagement indicators
        engagement_boost = 0.0
        for level, patterns in self.behavioral_indicators.items():
            if level == 'time_patterns':
                continue
            for pattern in patterns:
                if pattern in text:
                    if level == 'high_engagement':
                        engagement_boost += 0.3
                    else:
                        engagement_boost += 0.1
        
        # Boost for venue mentions
        venue_boost = 0.0
        for venue in category_data.get('venues', []):
            if venue in text:
                venue_boost += 0.1
        
        # Boost for activity mentions
        activity_boost = 0.0
        for activity in category_data.get('activities', []):
            if activity in text:
                activity_boost += 0.1
        
        total_confidence = min(
            base_confidence + engagement_boost + venue_boost + activity_boost,
            1.0
        )
        
        return total_confidence
    
    def _extract_evidence(self, text: str, matches: List[str]) -> str:
        """Extract evidence sentences containing keyword matches"""
        sentences = re.split(r'[.!?]+', text)
        evidence_sentences = []
        
        for sentence in sentences:
            if any(match in sentence.lower() for match in matches):
                evidence_sentences.append(sentence.strip())
        
        return ' '.join(evidence_sentences[:2])  # Top 2 evidence sentences
    
    def extract_behavioral_patterns(self, text: str) -> Dict[str, float]:
        """Extract behavioral patterns from text"""
        text_lower = text.lower()
        patterns = {}
        
        for pattern_type, indicators in self.behavioral_indicators.items():
            if pattern_type == 'time_patterns':
                patterns[pattern_type] = {}
                for time_type, time_indicators in indicators.items():
                    score = sum(1 for indicator in time_indicators if indicator in text_lower)
                    patterns[pattern_type][time_type] = score / len(time_indicators)
            else:
                score = sum(1 for indicator in indicators if indicator in text_lower)
                patterns[pattern_type] = score / len(indicators)
        
        return patterns
    
    def extract_activity_context(self, activity_text: str) -> Dict[str, Any]:
        """Extract context from activity description"""
        if not activity_text:
            return {}
        
        activity_lower = activity_text.lower()
        context = {}
        
        for context_type, context_data in self.activity_contexts.items():
            for level, indicators in context_data.items():
                if any(indicator in activity_lower for indicator in indicators):
                    context[context_type] = level
                    break
        
        return context


class EnhancedBackgroundSearchService:
    """Enhanced background search service with advanced personalization"""
    
    def __init__(self, config: Dict[str, Any] = None):
        from config.settings import SEARCH_CONFIG
        
        self.config = config or SEARCH_CONFIG
        self.session = None
        self.interest_extractor = AdvancedInterestExtractor()
        
    def _setup_session(self) -> requests.Session:
        """Setup requests session with retries and proper headers"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': self.config.get('USER_AGENT', 'WhatNowAI/1.0'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def search_enhanced_user_info(self, user_profile) -> EnhancedUserProfile:
        """
        Enhanced search that extracts detailed personalization data
        
        Args:
            user_profile: Basic user profile
            
        Returns:
            Enhanced user profile with personalization insights
        """
        logger.info(f"Starting enhanced search for user: {user_profile.name}")
        
        enhanced_profile = EnhancedUserProfile(
            name=user_profile.name,
            location=user_profile.location,
            social_handles=user_profile.social_handles,
            activity=user_profile.activity
        )
        
        if not self.session:
            self.session = self._setup_session()
        
        start_time = time.time()
        search_timeout = 15  # Increased timeout for better results
        
        try:
            # Extract insights from user's activity description
            if user_profile.activity:
                activity_insights = self.interest_extractor.extract_insights(
                    user_profile.activity, 'user_input', 'primary_activity'
                )
                for insight in activity_insights:
                    enhanced_profile.add_insight(insight)
                
                # Extract behavioral patterns
                enhanced_profile.behavioral_patterns = self.interest_extractor.extract_behavioral_patterns(
                    user_profile.activity
                )
                
                # Extract activity context
                enhanced_profile.activity_preferences = self.interest_extractor.extract_activity_context(
                    user_profile.activity
                )
            
            # Search social media for additional insights
            if user_profile.social_handles and (time.time() - start_time < search_timeout):
                social_insights = self._search_social_media_enhanced(user_profile.social_handles)
                for insight in social_insights:
                    enhanced_profile.add_insight(insight)
                
                # Extract social context
                enhanced_profile.social_context = self._analyze_social_context(user_profile.social_handles)
            
            # Search location-specific information
            if user_profile.location and (time.time() - start_time < search_timeout):
                location_insights = self._search_location_enhanced(user_profile.location, user_profile.activity)
                for insight in location_insights:
                    enhanced_profile.add_insight(insight)
                
                # Extract location context
                enhanced_profile.location_insights = self._analyze_location_context(user_profile.location)
            
            # Search activity-specific information
            if user_profile.activity and (time.time() - start_time < search_timeout):
                activity_insights = self._search_activity_enhanced(user_profile.activity, user_profile.location)
                for insight in activity_insights:
                    enhanced_profile.add_insight(insight)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Enhanced search completed in {elapsed_time:.1f}s with {len(enhanced_profile.interests)} insights")
            
        except Exception as e:
            logger.error(f"Error during enhanced search: {str(e)}")
        
        return enhanced_profile
    
    def _search_social_media_enhanced(self, social_handles: Dict[str, str]) -> List[PersonalizationInsight]:
        """Enhanced social media search with insight extraction"""
        insights = []
        
        for platform, handle in social_handles.items():
            if not handle:
                continue
            
            try:
                if platform.lower() == 'github':
                    github_insights = self._search_github_enhanced(handle)
                    insights.extend(github_insights)
                else:
                    platform_insights = self._search_platform_enhanced(platform, handle)
                    insights.extend(platform_insights)
                    
            except Exception as e:
                logger.warning(f"Failed to search {platform} for {handle}: {str(e)}")
                continue
        
        return insights
    
    def _search_github_enhanced(self, handle: str) -> List[PersonalizationInsight]:
        """Enhanced GitHub search with detailed insight extraction"""
        insights = []
        
        try:
            # Get user profile
            api_url = f"https://api.github.com/users/{handle}"
            response = self.session.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract insights from bio and profile
                bio_text = f"{data.get('bio', '')} {data.get('company', '')} {data.get('location', '')}"
                if bio_text.strip():
                    bio_insights = self.interest_extractor.extract_insights(
                        bio_text, 'github_profile', 'user_bio'
                    )
                    insights.extend(bio_insights)
                
                # Get repositories for additional insights
                repos_url = f"https://api.github.com/users/{handle}/repos?sort=updated&per_page=10"
                repos_response = self.session.get(repos_url, timeout=5)
                
                if repos_response.status_code == 200:
                    repos_data = repos_response.json()
                    
                    # Extract insights from repository names and descriptions
                    repo_text = ""
                    languages = set()
                    
                    for repo in repos_data:
                        repo_text += f"{repo.get('name', '')} {repo.get('description', '')} "
                        if repo.get('language'):
                            languages.add(repo['language'].lower())
                    
                    if repo_text.strip():
                        repo_insights = self.interest_extractor.extract_insights(
                            repo_text, 'github_repos', 'project_analysis'
                        )
                        insights.extend(repo_insights)
                    
                    # Add technology insight based on languages
                    if languages:
                        tech_insight = PersonalizationInsight(
                            category='technology',
                            keywords=list(languages),
                            confidence=0.8,
                            evidence=f"Active in programming languages: {', '.join(languages)}",
                            source='github_languages',
                            context='programming_languages'
                        )
                        insights.append(tech_insight)
                        
        except Exception as e:
            logger.warning(f"GitHub enhanced search failed for {handle}: {str(e)}")
        
        return insights
    
    def _search_platform_enhanced(self, platform: str, handle: str) -> List[PersonalizationInsight]:
        """Enhanced platform search with insight extraction"""
        insights = []
        
        try:
            # Search for platform-specific information
            query = quote_plus(f"site:{platform}.com {handle}")
            url = f"https://duckduckgo.com/html/?q={query}"
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract text from search results
                result_text = ""
                for result in soup.find_all('div', class_='result')[:3]:
                    title = result.find('a', class_='result__a')
                    snippet = result.find('a', class_='result__snippet')
                    
                    if title:
                        result_text += title.get_text() + " "
                    if snippet:
                        result_text += snippet.get_text() + " "
                
                if result_text.strip():
                    platform_insights = self.interest_extractor.extract_insights(
                        result_text, f'{platform}_search', f'social_media_{platform}'
                    )
                    insights.extend(platform_insights)
                    
        except Exception as e:
            logger.warning(f"Platform search failed for {platform}: {str(e)}")
        
        return insights
    
    def _search_location_enhanced(self, location: str, activity: str = "") -> List[PersonalizationInsight]:
        """Enhanced location search with insight extraction"""
        insights = []
        
        # Focus on activity-specific location searches
        queries = [
            f"things to do {location}",
            f"events {location}",
            f"activities {location}"
        ]
        
        if activity:
            queries.append(f"{activity} {location}")
            queries.append(f"{activity} classes {location}")
        
        for query in queries[:3]:  # Limit for performance
            try:
                encoded_query = quote_plus(query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract location-specific insights
                    result_text = ""
                    for result in soup.find_all('div', class_='result')[:2]:
                        snippet = result.find('a', class_='result__snippet')
                        if snippet:
                            result_text += snippet.get_text() + " "
                    
                    if result_text.strip():
                        location_insights = self.interest_extractor.extract_insights(
                            result_text, 'location_search', f'local_activities_{location}'
                        )
                        insights.extend(location_insights)
                        
            except Exception as e:
                logger.warning(f"Location search failed for {query}: {str(e)}")
                continue
        
        return insights
    
    def _search_activity_enhanced(self, activity: str, location: str = "") -> List[PersonalizationInsight]:
        """Enhanced activity search with insight extraction"""
        insights = []
        
        # Activity-focused searches
        queries = [
            f"how to {activity}",
            f"{activity} beginner guide",
            f"{activity} tips"
        ]
        
        if location:
            queries.append(f"{activity} {location}")
        
        for query in queries[:3]:  # Limit for performance
            try:
                encoded_query = quote_plus(query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract activity-specific insights
                    result_text = ""
                    for result in soup.find_all('div', class_='result')[:2]:
                        snippet = result.find('a', class_='result__snippet')
                        if snippet:
                            result_text += snippet.get_text() + " "
                    
                    if result_text.strip():
                        activity_insights = self.interest_extractor.extract_insights(
                            result_text, 'activity_search', f'activity_guidance_{activity}'
                        )
                        insights.extend(activity_insights)
                        
            except Exception as e:
                logger.warning(f"Activity search failed for {query}: {str(e)}")
                continue
        
        return insights
    
    def _analyze_social_context(self, social_handles: Dict[str, str]) -> Dict[str, Any]:
        """Analyze social media context for personalization"""
        context = {}
        
        active_platforms = [platform for platform, handle in social_handles.items() if handle]
        context['active_platforms'] = active_platforms
        context['platform_count'] = len(active_platforms)
        
        # Infer social preferences based on platforms
        if 'github' in active_platforms:
            context['tech_oriented'] = True
        if 'linkedin' in active_platforms:
            context['professional_oriented'] = True
        if 'instagram' in active_platforms or 'tiktok' in active_platforms:
            context['visual_oriented'] = True
        if 'twitter' in active_platforms:
            context['communication_oriented'] = True
        
        return context
    
    def _analyze_location_context(self, location: str) -> Dict[str, Any]:
        """Analyze location context for personalization"""
        context = {}
        
        # Extract location components
        location_parts = location.split(',')
        if len(location_parts) >= 2:
            context['city'] = location_parts[0].strip()
            context['country'] = location_parts[-1].strip()
        
        # Infer location characteristics (this could be enhanced with a location database)
        location_lower = location.lower()
        
        if any(city in location_lower for city in ['new york', 'london', 'tokyo', 'paris', 'san francisco']):
            context['urban_environment'] = True
            context['cultural_diversity'] = True
        
        if any(indicator in location_lower for indicator in ['beach', 'coast', 'island']):
            context['coastal_location'] = True
        
        if any(indicator in location_lower for indicator in ['mountain', 'valley', 'rural']):
            context['nature_access'] = True
        
        return context
    
    def generate_personalization_summary(self, enhanced_profile: EnhancedUserProfile) -> Dict[str, Any]:
        """Generate comprehensive personalization summary"""
        top_interests = enhanced_profile.get_top_interests(10)
        
        summary = {
            'user_profile': {
                'name': enhanced_profile.name,
                'location': enhanced_profile.location,
                'primary_activity': enhanced_profile.activity
            },
            'interests': [insight.to_dict() for insight in top_interests],
            'behavioral_patterns': enhanced_profile.behavioral_patterns,
            'activity_preferences': enhanced_profile.activity_preferences,
            'social_context': enhanced_profile.social_context,
            'location_insights': enhanced_profile.location_insights,
            'personalization_score': self._calculate_personalization_score(enhanced_profile),
            'recommendation_context': self._generate_recommendation_context(enhanced_profile)
        }
        
        return summary
    
    def _calculate_personalization_score(self, profile: EnhancedUserProfile) -> float:
        """Calculate how much personalization data we have"""
        score = 0.0
        
        # Base score for basic info
        if profile.name: score += 10
        if profile.location: score += 10
        if profile.activity: score += 20
        
        # Score for interests
        score += min(len(profile.interests) * 5, 30)
        
        # Score for behavioral patterns
        if profile.behavioral_patterns: score += 15
        
        # Score for social context
        if profile.social_context: score += 10
        
        # Score for location insights
        if profile.location_insights: score += 5
        
        return min(score, 100.0)
    
    def _generate_recommendation_context(self, profile: EnhancedUserProfile) -> Dict[str, Any]:
        """Generate context for event recommendations"""
        top_interests = profile.get_top_interests(5)
        
        context = {
            'primary_interests': [interest.category for interest in top_interests],
            'interest_keywords': [],
            'behavioral_preferences': {},
            'activity_context': profile.activity_preferences,
            'social_preferences': profile.social_context,
            'location_context': profile.location_insights
        }
        
        # Collect all keywords from top interests
        for interest in top_interests:
            context['interest_keywords'].extend(interest.keywords[:3])  # Top 3 keywords per interest
        
        # Extract key behavioral preferences
        if profile.behavioral_patterns:
            for pattern, score in profile.behavioral_patterns.items():
                if score > 0.3:  # Significant pattern
                    context['behavioral_preferences'][pattern] = score
        
        return context


# Enhanced convenience function
def perform_enhanced_background_search(user_profile) -> Dict[str, Any]:
    """
    Perform enhanced background search with detailed personalization data
    
    Args:
        user_profile: Basic user profile
        
    Returns:
        Dictionary containing enhanced personalization data
    """
    search_service = EnhancedBackgroundSearchService()
    
    try:
        # Perform enhanced search
        enhanced_profile = search_service.search_enhanced_user_info(user_profile)
        
        # Generate comprehensive summary
        personalization_summary = search_service.generate_personalization_summary(enhanced_profile)
        
        # Generate traditional summaries for backward compatibility
        traditional_summaries = {
            'general': f"Enhanced profile analysis completed with {len(enhanced_profile.interests)} interests identified.",
            'social': f"Social media analysis found {len(enhanced_profile.social_context)} platform insights.",
            'location': f"Location analysis for {enhanced_profile.location} completed.",
            'activity': f"Activity analysis for '{enhanced_profile.activity}' with context extraction completed."
        }
        
        return {
            'enhanced_personalization': personalization_summary,
            'raw_results': {
                'interests': [insight.to_dict() for insight in enhanced_profile.interests],
                'behavioral_patterns': enhanced_profile.behavioral_patterns,
                'social_context': enhanced_profile.social_context,
                'location_insights': enhanced_profile.location_insights
            },
            'summaries': traditional_summaries,
            'total_results': len(enhanced_profile.interests),
            'personalization_score': personalization_summary['personalization_score']
        }
        
    finally:
        if hasattr(search_service, 'session') and search_service.session:
            search_service.session.close()