"""
Enhanced User Profiling Service

This service creates comprehensive user profiles by analyzing multiple data sources
and extracting detailed interests, preferences, and behavioral patterns to improve
event recommendations and personalization.
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class UserInterest:
    """Detailed user interest with confidence metrics"""
    category: str
    keywords: List[str]
    confidence: float
    source: str
    evidence: str
    frequency: int = 1
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'keywords': self.keywords,
            'confidence': self.confidence,
            'source': self.source,
            'evidence': self.evidence,
            'frequency': self.frequency,
            'context': self.context
        }


@dataclass
class UserProfile:
    """Comprehensive user profile with behavioral insights"""
    name: str
    location: Dict[str, Any]
    activity: str
    social_data: Dict[str, str] = field(default_factory=dict)
    
    # Enhanced profile data
    interests: List[UserInterest] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    behavioral_patterns: Dict[str, Any] = field(default_factory=dict)
    demographic_hints: Dict[str, Any] = field(default_factory=dict)
    activity_context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    profile_completion: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_interest(self, interest: UserInterest):
        """Add interest with deduplication and scoring"""
        for existing in self.interests:
            if existing.category == interest.category and existing.source == interest.source:
                # Merge and update
                existing.keywords.extend(interest.keywords)
                existing.keywords = list(set(existing.keywords))
                existing.confidence = max(existing.confidence, interest.confidence)
                existing.frequency += 1
                return
        self.interests.append(interest)
    
    def get_top_interests(self, n: int = 10) -> List[UserInterest]:
        """Get top N interests by confidence and frequency"""
        return sorted(
            self.interests, 
            key=lambda x: (x.confidence * x.frequency), 
            reverse=True
        )[:n]
    
    def calculate_completion(self):
        """Calculate profile completion percentage"""
        score = 0.0
        
        # Basic info (20%)
        if self.name: score += 5
        if self.location.get('city'): score += 5
        if self.activity: score += 10
        
        # Social data (20%)
        social_count = len([v for v in self.social_data.values() if v])
        score += min(social_count * 3, 20)
        
        # Interests (30%)
        interest_score = min(len(self.interests) * 3, 30)
        score += interest_score
        
        # Preferences (15%)
        if self.preferences: score += 15
        
        # Behavioral patterns (15%)
        if self.behavioral_patterns: score += 15
        
        self.profile_completion = min(score, 100.0)
        return self.profile_completion


class AdvancedInterestExtractor:
    """Advanced interest extraction with NLP and context analysis"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.interest_taxonomy = self._load_interest_taxonomy()
        self.contextual_patterns = self._load_contextual_patterns()
        self.sentiment_indicators = self._load_sentiment_indicators()
    
    def _load_interest_taxonomy(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive interest taxonomy with hierarchical categories"""
        return {
            'music': {
                'keywords': [
                    'music', 'concert', 'festival', 'band', 'artist', 'album', 'song',
                    'guitar', 'piano', 'drums', 'violin', 'jazz', 'rock', 'pop', 'classical',
                    'hip-hop', 'rap', 'electronic', 'edm', 'country', 'blues', 'reggae',
                    'spotify', 'soundcloud', 'vinyl', 'live music', 'symphony', 'opera'
                ],
                'subcategories': ['instruments', 'genres', 'venues', 'streaming', 'recording'],
                'indicators': ['plays', 'listens', 'performs', 'composes', 'produces'],
                'venues': ['concert hall', 'club', 'stadium', 'amphitheater', 'bar'],
                'sentiment_boost': ['love', 'passion', 'obsessed', 'favorite', 'amazing']
            },
            'sports': {
                'keywords': [
                    'sports', 'football', 'basketball', 'baseball', 'soccer', 'tennis',
                    'golf', 'hockey', 'swimming', 'running', 'cycling', 'fitness', 'gym',
                    'marathon', 'triathlon', 'yoga', 'pilates', 'crossfit', 'weightlifting',
                    'volleyball', 'softball', 'wrestling', 'boxing', 'mma', 'skiing'
                ],
                'subcategories': ['team_sports', 'individual_sports', 'fitness', 'outdoor'],
                'indicators': ['plays', 'trains', 'competes', 'coaches', 'watches'],
                'venues': ['stadium', 'gym', 'court', 'field', 'track', 'pool'],
                'sentiment_boost': ['competitive', 'athletic', 'active', 'champion']
            },
            'arts': {
                'keywords': [
                    'art', 'painting', 'drawing', 'sculpture', 'photography', 'gallery',
                    'museum', 'exhibition', 'artist', 'creative', 'design', 'theater',
                    'drama', 'acting', 'dance', 'ballet', 'contemporary', 'crafts',
                    'pottery', 'jewelry', 'fashion', 'illustration', 'digital art'
                ],
                'subcategories': ['visual_arts', 'performing_arts', 'crafts', 'design'],
                'indicators': ['creates', 'exhibits', 'performs', 'designs', 'collects'],
                'venues': ['gallery', 'museum', 'theater', 'studio', 'workshop'],
                'sentiment_boost': ['creative', 'artistic', 'expressive', 'inspiring']
            },
            'technology': {
                'keywords': [
                    'technology', 'programming', 'coding', 'software', 'developer',
                    'engineer', 'computer', 'ai', 'machine learning', 'data science',
                    'startup', 'app', 'website', 'github', 'python', 'javascript',
                    'blockchain', 'crypto', 'iot', 'robotics', 'vr', 'ar', 'gaming'
                ],
                'subcategories': ['programming', 'ai_ml', 'hardware', 'gaming', 'crypto'],
                'indicators': ['develops', 'codes', 'builds', 'programs', 'hacks'],
                'venues': ['hackathon', 'conference', 'meetup', 'coworking', 'lab'],
                'sentiment_boost': ['innovative', 'cutting-edge', 'passionate', 'expert']
            },
            'food': {
                'keywords': [
                    'food', 'cooking', 'baking', 'cuisine', 'restaurant', 'chef',
                    'recipe', 'culinary', 'dining', 'foodie', 'wine', 'beer', 'coffee',
                    'tea', 'organic', 'vegan', 'vegetarian', 'nutrition', 'gourmet',
                    'street food', 'fine dining', 'barbecue', 'dessert', 'cocktails'
                ],
                'subcategories': ['cooking', 'dining', 'beverages', 'nutrition', 'culture'],
                'indicators': ['cooks', 'bakes', 'tastes', 'reviews', 'explores'],
                'venues': ['restaurant', 'kitchen', 'market', 'festival', 'tasting'],
                'sentiment_boost': ['delicious', 'gourmet', 'passionate', 'expert']
            },
            'travel': {
                'keywords': [
                    'travel', 'tourism', 'vacation', 'trip', 'adventure', 'backpacking',
                    'hotel', 'flight', 'destination', 'explore', 'culture', 'sightseeing',
                    'beach', 'mountain', 'city', 'country', 'international', 'domestic',
                    'cruise', 'road trip', 'camping', 'hiking', 'photography'
                ],
                'subcategories': ['destinations', 'activities', 'accommodation', 'transport'],
                'indicators': ['visits', 'explores', 'travels', 'photographs', 'blogs'],
                'venues': ['destinations', 'hotels', 'airports', 'attractions', 'tours'],
                'sentiment_boost': ['wanderlust', 'adventure', 'explorer', 'globe-trotter']
            },
            'nature': {
                'keywords': [
                    'nature', 'outdoor', 'hiking', 'camping', 'wildlife', 'conservation',
                    'environment', 'ecology', 'sustainability', 'gardening', 'plants',
                    'animals', 'birds', 'forest', 'mountains', 'ocean', 'rivers',
                    'national parks', 'trails', 'fishing', 'hunting', 'photography'
                ],
                'subcategories': ['outdoor_activities', 'wildlife', 'conservation', 'gardening'],
                'indicators': ['hikes', 'camps', 'explores', 'photographs', 'conserves'],
                'venues': ['parks', 'trails', 'forests', 'lakes', 'mountains'],
                'sentiment_boost': ['eco-friendly', 'naturalist', 'outdoorsy', 'green']
            }
        }
    
    def _load_contextual_patterns(self) -> Dict[str, List[str]]:
        """Load patterns that indicate depth of interest"""
        return {
            'high_engagement': [
                'passionate about', 'obsessed with', 'love', 'dedicated to',
                'professional', 'expert', 'years of experience', 'certified',
                'compete', 'perform', 'teach', 'mentor', 'lead'
            ],
            'medium_engagement': [
                'enjoy', 'like', 'interested in', 'hobby', 'amateur',
                'learning', 'practicing', 'member', 'participant'
            ],
            'low_engagement': [
                'sometimes', 'occasionally', 'beginner', 'trying',
                'curious about', 'thinking about', 'might'
            ],
            'frequency_indicators': [
                'daily', 'weekly', 'monthly', 'regularly', 'often',
                'frequently', 'always', 'constantly', 'every day'
            ]
        }
    
    def _load_sentiment_indicators(self) -> Dict[str, float]:
        """Load sentiment indicators and their weights"""
        return {
            'love': 0.9, 'passion': 0.9, 'obsessed': 0.8, 'amazing': 0.7,
            'fantastic': 0.7, 'excellent': 0.6, 'great': 0.5, 'good': 0.4,
            'like': 0.3, 'okay': 0.2, 'hate': -0.8, 'terrible': -0.7,
            'awful': -0.6, 'bad': -0.5, 'dislike': -0.4
        }
    
    def extract_interests(self, text: str, source: str, context: str = "") -> List[UserInterest]:
        """Extract interests from text with advanced NLP analysis"""
        if not text:
            return []
        
        text_lower = text.lower()
        interests = []
        
        for category, category_data in self.interest_taxonomy.items():
            # Find keyword matches
            keyword_matches = self._find_keyword_matches(text_lower, category_data['keywords'])
            
            if keyword_matches:
                # Calculate confidence based on multiple factors
                confidence = self._calculate_confidence(
                    text_lower, keyword_matches, category_data
                )
                
                # Extract evidence and context
                evidence = self._extract_evidence(text, keyword_matches)
                interest_context = self._extract_context(text, keyword_matches)
                
                if confidence > 0.2:  # Minimum confidence threshold
                    interest = UserInterest(
                        category=category,
                        keywords=keyword_matches,
                        confidence=confidence,
                        source=source,
                        evidence=evidence,
                        context=f"{context} | {interest_context}".strip(" | ")
                    )
                    interests.append(interest)
        
        return interests
    
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
        for level, patterns in self.contextual_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    if level == 'high_engagement':
                        engagement_boost += 0.3
                    elif level == 'medium_engagement':
                        engagement_boost += 0.2
                    elif level == 'frequency_indicators':
                        engagement_boost += 0.15
        
        # Boost for sentiment
        sentiment_boost = 0.0
        for sentiment, weight in self.sentiment_indicators.items():
            if sentiment in text:
                sentiment_boost += weight * 0.1
        
        # Boost for venue/activity mentions
        venue_boost = 0.0
        for venue in category_data.get('venues', []):
            if venue in text:
                venue_boost += 0.1
        
        # Boost for action indicators
        action_boost = 0.0
        for indicator in category_data.get('indicators', []):
            if indicator in text:
                action_boost += 0.1
        
        total_confidence = min(
            base_confidence + engagement_boost + sentiment_boost + venue_boost + action_boost,
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
    
    def _extract_context(self, text: str, matches: List[str]) -> str:
        """Extract contextual information about the interest"""
        text_lower = text.lower()
        context_parts = []
        
        # Look for time indicators
        time_patterns = ['since', 'for', 'years', 'months', 'recently', 'started']
        for pattern in time_patterns:
            if pattern in text_lower:
                context_parts.append(f"temporal:{pattern}")
        
        # Look for skill level indicators
        skill_patterns = ['beginner', 'intermediate', 'advanced', 'professional', 'expert']
        for pattern in skill_patterns:
            if pattern in text_lower:
                context_parts.append(f"skill:{pattern}")
        
        return ', '.join(context_parts)


class BehavioralAnalyzer:
    """Analyze user behavior patterns from text and social data"""
    
    def __init__(self):
        self.behavior_patterns = self._load_behavior_patterns()
    
    def _load_behavior_patterns(self) -> Dict[str, List[str]]:
        """Load behavioral pattern indicators"""
        return {
            'social_learner': [
                'group', 'class', 'workshop', 'meetup', 'club', 'team',
                'community', 'together', 'friends', 'social'
            ],
            'solo_activities': [
                'alone', 'individual', 'personal', 'solo', 'private',
                'meditation', 'reading', 'writing', 'reflection'
            ],
            'adventure_seeker': [
                'adventure', 'extreme', 'adrenaline', 'challenge', 'risk',
                'new', 'explore', 'discover', 'unknown', 'exciting'
            ],
            'comfort_zone': [
                'familiar', 'routine', 'regular', 'same', 'usual',
                'comfortable', 'safe', 'known', 'predictable'
            ],
            'creative_expression': [
                'create', 'make', 'build', 'design', 'artistic',
                'original', 'unique', 'innovative', 'express'
            ],
            'learning_oriented': [
                'learn', 'study', 'education', 'knowledge', 'skill',
                'improve', 'develop', 'grow', 'understand', 'research'
            ],
            'health_conscious': [
                'healthy', 'wellness', 'fitness', 'nutrition', 'organic',
                'exercise', 'mindful', 'balance', 'wellbeing'
            ],
            'time_preferences': {
                'morning': ['morning', 'early', 'dawn', 'sunrise', 'am'],
                'evening': ['evening', 'night', 'sunset', 'pm', 'late'],
                'weekend': ['weekend', 'saturday', 'sunday', 'days off'],
                'weekday': ['weekday', 'workday', 'monday', 'friday']
            }
        }
    
    def analyze_behavior(self, text: str, social_data: Dict[str, str]) -> Dict[str, Any]:
        """Analyze behavioral patterns from user data"""
        text_lower = text.lower() if text else ""
        patterns = {}
        
        # Analyze text for behavioral indicators
        for pattern_type, keywords in self.behavior_patterns.items():
            if pattern_type == 'time_preferences':
                patterns[pattern_type] = {}
                for time_type, time_keywords in keywords.items():
                    score = sum(1 for keyword in time_keywords if keyword in text_lower)
                    patterns[pattern_type][time_type] = score / len(time_keywords)
            else:
                score = sum(1 for keyword in keywords if keyword in text_lower)
                patterns[pattern_type] = score / len(keywords)
        
        # Analyze social data for platform preferences
        platform_activity = {}
        for platform, handle in social_data.items():
            if handle:
                platform_activity[platform] = self._infer_platform_behavior(platform)
        
        patterns['platform_preferences'] = platform_activity
        
        return patterns
    
    def _infer_platform_behavior(self, platform: str) -> Dict[str, str]:
        """Infer behavioral traits from social platform usage"""
        platform_traits = {
            'twitter': {'communication': 'concise', 'engagement': 'public', 'content': 'news_opinion'},
            'instagram': {'communication': 'visual', 'engagement': 'aesthetic', 'content': 'lifestyle'},
            'linkedin': {'communication': 'professional', 'engagement': 'networking', 'content': 'career'},
            'github': {'communication': 'technical', 'engagement': 'collaborative', 'content': 'development'},
            'tiktok': {'communication': 'creative', 'engagement': 'viral', 'content': 'entertainment'},
            'youtube': {'communication': 'educational', 'engagement': 'educational', 'content': 'learning'}
        }
        return platform_traits.get(platform, {'communication': 'social', 'engagement': 'casual'})


class EnhancedUserProfilingService:
    """Main service for enhanced user profiling"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.interest_extractor = AdvancedInterestExtractor(config)
        self.behavior_analyzer = BehavioralAnalyzer()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def create_enhanced_profile(
        self, 
        name: str, 
        location: Dict[str, Any], 
        activity: str,
        social_data: Dict[str, str] = None,
        search_results: Dict[str, Any] = None
    ) -> UserProfile:
        """Create comprehensive user profile with advanced analysis"""
        
        logger.info(f"Creating enhanced profile for {name}")
        
        profile = UserProfile(
            name=name,
            location=location,
            activity=activity,
            social_data=social_data or {}
        )
        
        # Extract interests from activity description
        if activity:
            activity_interests = self.interest_extractor.extract_interests(
                activity, 'user_input', 'primary_activity'
            )
            for interest in activity_interests:
                profile.add_interest(interest)
        
        # Extract interests from search results if available
        if search_results:
            self._process_search_results(profile, search_results)
        
        # Analyze behavioral patterns
        all_text = f"{activity} {' '.join(social_data.values() if social_data else [])}"
        profile.behavioral_patterns = self.behavior_analyzer.analyze_behavior(
            all_text, social_data or {}
        )
        
        # Infer demographic hints
        profile.demographic_hints = self._infer_demographics(profile)
        
        # Analyze activity context
        profile.activity_context = self._analyze_activity_context(activity)
        
        # Set preferences based on analysis
        profile.preferences = self._generate_preferences(profile)
        
        # Calculate profile completion
        profile.calculate_completion()
        
        logger.info(f"Enhanced profile created with {len(profile.interests)} interests "
                   f"and {profile.profile_completion:.1f}% completion")
        
        return profile
    
    def _process_search_results(self, profile: UserProfile, search_results: Dict[str, Any]):
        """Process search results to extract additional interests and context"""
        
        # Process search summaries
        summaries = search_results.get('search_summaries', {})
        for source, summary in summaries.items():
            if summary and isinstance(summary, str):
                interests = self.interest_extractor.extract_interests(
                    summary, f'search_{source}', source
                )
                for interest in interests:
                    profile.add_interest(interest)
        
        # Process raw search results if available
        raw_results = search_results.get('search_results', {})
        for source, results in raw_results.items():
            if isinstance(results, list):
                for result in results[:3]:  # Process top 3 results per source
                    if isinstance(result, dict):
                        content = result.get('content', '')
                        if content:
                            interests = self.interest_extractor.extract_interests(
                                content, f'search_{source}', 'web_content'
                            )
                            for interest in interests:
                                profile.add_interest(interest)
    
    def _infer_demographics(self, profile: UserProfile) -> Dict[str, Any]:
        """Infer demographic hints from profile data"""
        demographics = {}
        
        # Age group inference from interests and language
        young_adult_indicators = ['college', 'university', 'student', 'party', 'club', 'gaming']
        middle_age_indicators = ['family', 'career', 'professional', 'mortgage', 'kids']
        senior_indicators = ['retirement', 'grandchildren', 'volunteer', 'garden']
        
        all_text = f"{profile.activity} {' '.join([i.evidence for i in profile.interests])}"
        text_lower = all_text.lower()
        
        young_score = sum(1 for indicator in young_adult_indicators if indicator in text_lower)
        middle_score = sum(1 for indicator in middle_age_indicators if indicator in text_lower)
        senior_score = sum(1 for indicator in senior_indicators if indicator in text_lower)
        
        if young_score > middle_score and young_score > senior_score:
            demographics['age_group_hint'] = 'young_adult'
        elif middle_score > senior_score:
            demographics['age_group_hint'] = 'middle_age'
        elif senior_score > 0:
            demographics['age_group_hint'] = 'senior'
        
        # Lifestyle inference
        if any(cat in ['fitness', 'sports', 'nature'] for cat in [i.category for i in profile.interests]):
            demographics['lifestyle_hint'] = 'active'
        elif any(cat in ['arts', 'music', 'technology'] for cat in [i.category for i in profile.interests]):
            demographics['lifestyle_hint'] = 'creative'
        elif any(cat in ['food', 'travel', 'culture'] for cat in [i.category for i in profile.interests]):
            demographics['lifestyle_hint'] = 'experiential'
        
        return demographics
    
    def _analyze_activity_context(self, activity: str) -> Dict[str, Any]:
        """Analyze the context and intent behind user's activity request"""
        if not activity:
            return {}
        
        activity_lower = activity.lower()
        context = {}
        
        # Intent analysis
        if any(word in activity_lower for word in ['want', 'need', 'looking for', 'search']):
            context['intent'] = 'seeking'
        elif any(word in activity_lower for word in ['love', 'enjoy', 'passion']):
            context['intent'] = 'pursuing_interest'
        elif any(word in activity_lower for word in ['learn', 'try', 'new']):
            context['intent'] = 'exploring'
        
        # Urgency analysis
        if any(word in activity_lower for word in ['tonight', 'today', 'now', 'immediate']):
            context['urgency'] = 'high'
        elif any(word in activity_lower for word in ['weekend', 'soon', 'this week']):
            context['urgency'] = 'medium'
        else:
            context['urgency'] = 'low'
        
        # Social context
        if any(word in activity_lower for word in ['with friends', 'group', 'family', 'date']):
            context['social_setting'] = 'group'
        elif any(word in activity_lower for word in ['alone', 'solo', 'myself']):
            context['social_setting'] = 'solo'
        else:
            context['social_setting'] = 'flexible'
        
        # Budget hints
        if any(word in activity_lower for word in ['free', 'cheap', 'budget', 'affordable']):
            context['budget_preference'] = 'low'
        elif any(word in activity_lower for word in ['premium', 'high-end', 'luxury', 'expensive']):
            context['budget_preference'] = 'high'
        else:
            context['budget_preference'] = 'medium'
        
        return context
    
    def _generate_preferences(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate user preferences based on profile analysis"""
        preferences = {}
        
        # Event type preferences based on interests
        top_interests = profile.get_top_interests(5)
        preferences['preferred_categories'] = [i.category for i in top_interests]
        
        # Time preferences from behavioral patterns
        time_prefs = profile.behavioral_patterns.get('time_preferences', {})
        if time_prefs:
            preferred_time = max(time_prefs, key=time_prefs.get)
            preferences['preferred_time'] = preferred_time
        
        # Social preferences
        if profile.behavioral_patterns.get('social_learner', 0) > 0.3:
            preferences['social_preference'] = 'group'
        elif profile.behavioral_patterns.get('solo_activities', 0) > 0.3:
            preferences['social_preference'] = 'solo'
        else:
            preferences['social_preference'] = 'flexible'
        
        # Activity style preferences
        if profile.behavioral_patterns.get('adventure_seeker', 0) > 0.3:
            preferences['activity_style'] = 'adventurous'
        elif profile.behavioral_patterns.get('learning_oriented', 0) > 0.3:
            preferences['activity_style'] = 'educational'
        elif profile.behavioral_patterns.get('creative_expression', 0) > 0.3:
            preferences['activity_style'] = 'creative'
        else:
            preferences['activity_style'] = 'balanced'
        
        # Budget preference from activity context
        budget_pref = profile.activity_context.get('budget_preference', 'medium')
        preferences['budget_preference'] = budget_pref
        
        return preferences
    
    def get_recommendation_context(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate context for event recommendations"""
        return {
            'user_profile': {
                'name': profile.name,
                'location': profile.location,
                'primary_activity': profile.activity,
                'completion_score': profile.profile_completion
            },
            'interests': [i.to_dict() for i in profile.get_top_interests(10)],
            'preferences': profile.preferences,
            'behavioral_patterns': profile.behavioral_patterns,
            'activity_context': profile.activity_context,
            'demographic_hints': profile.demographic_hints
        }
