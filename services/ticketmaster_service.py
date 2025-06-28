"""
Ticketmaster API service for event discovery

This module integrates with the Ticketmaster Discovery API to find local events
and activities based on user location and interests. Includes advanced personalization,
event categorization, filtering, and comprehensive error handling for intelligent
event discovery that adapts to user preferences and behavioral patterns.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Enhanced event data structure with personalization metrics"""
    id: str
    name: str
    url: str
    date: str
    time: str
    venue: str
    address: str
    city: str
    latitude: float
    longitude: float
    category: str
    subcategory: str = ""
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    image_url: str = ""
    description: str = ""
    
    # Enhanced fields for personalization
    relevance_score: float = 0.0
    personalization_factors: Dict[str, float] = None
    recommendation_reason: str = ""
    interest_matches: List[str] = None
    behavioral_fit: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.personalization_factors is None:
            self.personalization_factors = {}
        if self.interest_matches is None:
            self.interest_matches = []
        if self.behavioral_fit is None:
            self.behavioral_fit = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'date': self.date,
            'time': self.time,
            'venue': self.venue,
            'address': self.address,
            'city': self.city,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'category': self.category,
            'subcategory': self.subcategory,
            'price_min': self.price_min,
            'price_max': self.price_max,
            'image_url': self.image_url,
            'description': self.description,
            'relevance_score': getattr(self, 'relevance_score', 0.0),
            'personalization_factors': getattr(self, 'personalization_factors', {}),
            'recommendation_reason': getattr(self, 'recommendation_reason', ''),
            'interest_matches': getattr(self, 'interest_matches', []),
            'behavioral_fit': getattr(self, 'behavioral_fit', {}),
            'ai_analysis': {
                'score': getattr(self, 'personalization_factors', {}).get('ai_score', 0),
                'confidence': getattr(self, 'personalization_factors', {}).get('ai_confidence', 0),
                'reason': getattr(self, 'personalization_factors', {}).get('ai_reason', '')
            }
        }


class TicketmasterService:
    """Advanced service for intelligent event discovery with personalization"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        """
        Initialize Ticketmaster service
        
        Args:
            api_key: Ticketmaster API key
            config: Configuration dictionary
        """
        self.api_key = api_key
        self.config = config
        self.base_url = config.get('BASE_URL', 'https://app.ticketmaster.com/discovery/v2')
        self.session = requests.Session()
        
        # Enhanced personalization components
        self.category_mapper = self._init_category_mapper()
        self.preference_analyzer = self._init_preference_analyzer()
        self.behavioral_filter = self._init_behavioral_filter()
        
    def search_events(self, location: Dict[str, Any], user_interests: List[str] = None, 
                     user_activity: str = "", personalization_data: Dict[str, Any] = None,
                     user_profile: Any = None) -> List[Event]:
        """
        Search for events near a location based on user interests and enhanced personalization
        
        Args:
            location: Dictionary with latitude, longitude, city, country
            user_interests: List of user interest categories
            user_activity: What the user wants to do
            personalization_data: Enhanced personalization data from background search
            user_profile: Enhanced user profile from user_profiling_service
            
        Returns:
            List of Event objects filtered and ranked by AI and user preferences
        """
        if not self.api_key:
            logger.warning("Ticketmaster API key not provided")
            return []
        
        latitude = location.get('latitude')
        longitude = location.get('longitude')
        
        # Convert to float if needed
        try:
            if latitude is not None:
                latitude = float(latitude)
            if longitude is not None:
                longitude = float(longitude)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert coordinates to float in Ticketmaster service: {e}")
            return []
        
        if not latitude or not longitude:
            logger.warning("Location coordinates not provided or invalid")
            return []
        
        logger.info(f"Searching events with AI-enhanced personalization: "
                   f"location=({latitude},{longitude}), "
                   f"basic_interests={user_interests}, "
                   f"activity='{user_activity}', "
                   f"has_personalization_data={bool(personalization_data)}, "
                   f"has_user_profile={bool(user_profile)}")
        
        events = []
        
        try:
            # Create enhanced personalization data that includes user profile
            enhanced_personalization = self._merge_personalization_data(
                personalization_data, user_profile, user_activity
            )
            
            # Extract enhanced interests from all sources
            enhanced_interests = self._extract_enhanced_interests(
                enhanced_personalization, user_interests, user_activity
            )
            
            # Search for events based on location
            base_events = self._search_by_location(latitude, longitude)
            events.extend(base_events)
            
            # Search for events based on enhanced user profile
            if enhanced_interests['categories'] or user_activity:
                interest_events = self._search_by_enhanced_interests(
                    latitude, longitude, enhanced_interests, user_activity
                )
                events.extend(interest_events)
            
            # Remove duplicates based on event ID
            unique_events = {event.id: event for event in events}
            events = list(unique_events.values())
            
            # Filter and rank events using AI and personalization
            events = self._filter_and_rank_events(events, enhanced_interests, enhanced_personalization)
            
            # Sort by relevance score (highest first) then by date
            events.sort(key=lambda e: (-getattr(e, 'relevance_score', 0), e.date))
            
            # Limit results
            max_events = self.config.get('MAX_EVENTS', 20)
            final_events = events[:max_events]
            
            # Add personalization metadata to events
            self._add_personalization_metadata(final_events, enhanced_interests, enhanced_personalization)
            
            logger.info(f"AI-enhanced search completed: {len(final_events)} events returned")
            
            return final_events
            
        except Exception as e:
            logger.error(f"Error searching Ticketmaster events: {e}")
            return []
    
    def _merge_personalization_data(self, personalization_data: Dict[str, Any], 
                                   user_profile: Any, user_activity: str) -> Dict[str, Any]:
        """Merge personalization data from different sources"""
        merged_data = personalization_data.copy() if personalization_data else {}
        
        # Add user activity
        merged_data['activity'] = user_activity
        
        # If we have minimal data, ensure we have at least basic context
        if not merged_data and user_activity:
            logger.info("Creating minimal personalization context from activity")
            merged_data = {
                'activity': user_activity,
                'user_profile': {
                    'primary_activity': user_activity,
                    'interests': [],
                    'preferences': {'activity_style': 'balanced'},
                    'behavioral_patterns': {},
                    'activity_context': {'intent': 'seeking'},
                    'completion_score': 10
                },
                'minimal_context': True
            }
        
        # Add user profile data if available
        if user_profile:
            try:
                # Get recommendation context from enhanced user profile
                from services.user_profiling_service import EnhancedUserProfilingService
                
                if hasattr(user_profile, 'get_top_interests'):
                    # It's a UserProfile object
                    merged_data['user_profile'] = {
                        'name': user_profile.name,
                        'location': user_profile.location,
                        'primary_activity': user_profile.activity,
                        'completion_score': getattr(user_profile, 'profile_completion', 0),
                        'interests': [i.to_dict() for i in user_profile.get_top_interests(10)],
                        'preferences': getattr(user_profile, 'preferences', {}),
                        'behavioral_patterns': getattr(user_profile, 'behavioral_patterns', {}),
                        'activity_context': getattr(user_profile, 'activity_context', {}),
                        'demographic_hints': getattr(user_profile, 'demographic_hints', {})
                    }
                elif isinstance(user_profile, dict):
                    # It's already a dictionary
                    merged_data['user_profile'] = user_profile
                
            except Exception as e:
                logger.warning(f"Failed to merge user profile data: {e}")
        
        return merged_data
    
    def _add_personalization_metadata(self, events: List[Event], enhanced_interests: Dict[str, Any],
                                     personalization_data: Dict[str, Any]):
        """Add detailed personalization metadata to events"""
        for event in events:
            if not hasattr(event, 'personalization_factors'):
                setattr(event, 'personalization_factors', {})
            
            # Add interest matches
            event_text = f"{event.name} {event.description} {event.subcategory}".lower()
            keywords = enhanced_interests.get('keywords', [])
            
            matched_keywords = [kw for kw in keywords if kw.lower() in event_text]
            setattr(event, 'interest_matches', matched_keywords)
            
            # Add behavioral fit analysis
            user_profile = personalization_data.get('user_profile', {})
            behavioral_patterns = user_profile.get('behavioral_patterns', {})
            preferences = user_profile.get('preferences', {})
            
            behavioral_fit = {}
            
            # Social preference fit
            social_pref = preferences.get('social_preference', 'flexible')
            if social_pref != 'flexible':
                if social_pref == 'group' and event.category in ['music', 'sports']:
                    behavioral_fit['social_fit'] = 'high'
                elif social_pref == 'solo' and event.category in ['arts']:
                    behavioral_fit['social_fit'] = 'high'
                else:
                    behavioral_fit['social_fit'] = 'medium'
            
            # Activity style fit
            activity_style = preferences.get('activity_style', 'balanced')
            if 'adventure' in activity_style and any(word in event_text for word in ['outdoor', 'extreme', 'adventure']):
                behavioral_fit['adventure_fit'] = 'high'
            elif 'creative' in activity_style and event.category == 'arts':
                behavioral_fit['creative_fit'] = 'high'
            elif 'educational' in activity_style and any(word in event_text for word in ['workshop', 'lecture', 'learn']):
                behavioral_fit['educational_fit'] = 'high'
            
            setattr(event, 'behavioral_fit', behavioral_fit)
            
            # Update personalization factors
            event.personalization_factors.update({
                'keyword_matches': len(matched_keywords),
                'category_relevance': 1.0 if event.category in enhanced_interests.get('categories', []) else 0.5,
                'behavioral_fit_score': len(behavioral_fit) / 3.0,  # Normalize by number of possible fits
                'user_profile_completion': user_profile.get('completion_score', 0) / 100.0
            })
    
    def _search_by_location(self, latitude: float, longitude: float) -> List[Event]:
        """Search for events by location"""
        events = []
        
        params = {
            'apikey': self.api_key,
            'latlong': f"{latitude},{longitude}",
            'radius': self.config.get('SEARCH_RADIUS', 50),
            'unit': 'miles',
            'size': 20,
            'sort': 'date,asc'
        }
        
        try:
            response = self._make_request('/events.json', params)
            if response and '_embedded' in response:
                events = self._parse_events(response['_embedded']['events'])
        except Exception as e:
            logger.error(f"Error searching events by location: {e}")
        
        return events
    
    def _search_by_interests(self, latitude: float, longitude: float, 
                           interests: List[str], activity: str) -> List[Event]:
        """Search for events based on user interests and activity"""
        events = []
        
        # Map user interests to Ticketmaster categories
        category_mapping = {
            'music': 'music',
            'sports': 'sports',
            'theater': 'arts',
            'comedy': 'arts',
            'family': 'family',
            'food': 'miscellaneous',
            'fitness': 'sports',
            'technology': 'miscellaneous',
            'art': 'arts',
            'dance': 'arts'
        }
        
        # Determine search categories
        search_categories = []
        if interests:
            for interest in interests:
                category = category_mapping.get(interest.lower())
                if category and category not in search_categories:
                    search_categories.append(category)
        
        # Use AI to determine category from activity if available
        if activity and not search_categories:
            search_categories = self._categorize_activity_with_ai(activity)
        
        # If no specific categories, use default
        if not search_categories:
            search_categories = self.config.get('DEFAULT_CATEGORIES', ['music', 'sports', 'arts'])
        
        # Search for each category
        for category in search_categories:
            try:
                params = {
                    'apikey': self.api_key,
                    'latlong': f"{latitude},{longitude}",
                    'radius': self.config.get('SEARCH_RADIUS', 50),
                    'unit': 'miles',
                    'size': 10,
                    'sort': 'date,asc',
                    'classificationName': category
                }
                
                response = self._make_request('/events.json', params)
                if response and '_embedded' in response:
                    category_events = self._parse_events(response['_embedded']['events'])
                    events.extend(category_events)
                    
            except Exception as e:
                logger.error(f"Error searching events for category {category}: {e}")
                continue
        
        return events
    
    def _categorize_activity_with_ai(self, activity: str) -> List[str]:
        """Use OpenAI to categorize user activity into Ticketmaster categories"""
        try:
            from config.settings import OPENAI_API_KEY
            if not OPENAI_API_KEY:
                return ['miscellaneous']
            
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            prompt = f"""
            Based on the activity "{activity}", suggest the most relevant Ticketmaster event categories.
            
            Available categories:
            - music (concerts, festivals, shows)
            - sports (games, tournaments, fitness events)
            - arts (theater, comedy, exhibitions, dance)
            - family (kid-friendly events)
            - miscellaneous (other events)
            
            Return only the category names as a comma-separated list, maximum 3 categories.
            Activity: {activity}
            Categories:
            """
            
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=50,
                temperature=0.3
            )
            
            categories_text = response.choices[0].text.strip()
            categories = [cat.strip().lower() for cat in categories_text.split(',')]
            
            # Validate categories
            valid_categories = ['music', 'sports', 'arts', 'family', 'miscellaneous']
            return [cat for cat in categories if cat in valid_categories]
            
        except Exception as e:
            logger.warning(f"AI categorization failed: {e}")
            return ['miscellaneous']
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a request to the Ticketmaster API"""
        url = self.base_url + endpoint
        
        try:
            response = self.session.get(
                url, 
                params=params, 
                timeout=self.config.get('TIMEOUT', 10)
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ticketmaster API request failed: {e}")
            return None
    
    def _parse_events(self, events_data: List[Dict[str, Any]]) -> List[Event]:
        """Parse events from Ticketmaster API response"""
        events = []
        
        for event_data in events_data:
            try:
                event = self._parse_single_event(event_data)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
                continue
        
        return events
    
    def _parse_single_event(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """Parse a single event from API response"""
        try:
            # Basic event info
            event_id = event_data.get('id', '')
            name = event_data.get('name', 'Unknown Event')
            url = event_data.get('url', '')
            
            # Date and time
            dates = event_data.get('dates', {})
            start = dates.get('start', {})
            date = start.get('localDate', '')
            time = start.get('localTime', '')
            
            # Venue information
            venues = event_data.get('_embedded', {}).get('venues', [])
            if not venues:
                return None
            
            venue_data = venues[0]
            venue_name = venue_data.get('name', 'Unknown Venue')
            
            # Address
            address_data = venue_data.get('address', {})
            address = address_data.get('line1', '')
            
            city_data = venue_data.get('city', {})
            city = city_data.get('name', '')
            
            # Coordinates
            location_data = venue_data.get('location', {})
            try:
                latitude = float(location_data.get('latitude', 0))
                longitude = float(location_data.get('longitude', 0))
            except (ValueError, TypeError):
                return None
            
            if not latitude or not longitude:
                return None
            
            # Category
            classifications = event_data.get('classifications', [])
            category = 'miscellaneous'
            subcategory = ''
            
            if classifications:
                segment = classifications[0].get('segment', {})
                genre = classifications[0].get('genre', {})
                category = segment.get('name', 'miscellaneous').lower()
                subcategory = genre.get('name', '')
            
            # Price information
            price_ranges = event_data.get('priceRanges', [])
            price_min = None
            price_max = None
            
            if price_ranges:
                price_min = price_ranges[0].get('min')
                price_max = price_ranges[0].get('max')
            
            # Images
            images = event_data.get('images', [])
            image_url = ''
            if images:
                # Get the largest image
                image_url = max(images, key=lambda img: img.get('width', 0) * img.get('height', 0)).get('url', '')
            
            # Description
            description = event_data.get('info', '')
            
            return Event(
                id=event_id,
                name=name,
                url=url,
                date=date,
                time=time,
                venue=venue_name,
                address=address,
                city=city,
                latitude=latitude,
                longitude=longitude,
                category=category,
                subcategory=subcategory,
                price_min=price_min,
                price_max=price_max,
                image_url=image_url,
                description=description
            )
            
        except Exception as e:
            logger.error(f"Error parsing event data: {e}")
            return None
    
    def _extract_enhanced_interests(self, personalization_data: Dict[str, Any], 
                                  basic_interests: List[str], activity: str) -> Dict[str, Any]:
        """
        Extract and combine interests from personalization data and basic inputs
        
        Args:
            personalization_data: Data from background search with interests
            basic_interests: Basic interest categories
            activity: User activity description
            
        Returns:
            Enhanced interests dictionary with categories, keywords, and confidence scores
        """
        enhanced_interests = {
            'categories': [],
            'keywords': [],
            'category_scores': {},
            'activity_keywords': []
        }
        
        # Start with basic interests
        if basic_interests:
            enhanced_interests['categories'].extend(basic_interests)
            for interest in basic_interests:
                enhanced_interests['category_scores'][interest] = 0.5  # Default confidence
        
        # Extract interests from personalization data
        if personalization_data:
            # Check for interests from background search
            search_results = personalization_data.get('search_results', {})
            search_summaries = personalization_data.get('search_summaries', {})
            
            # Extract from search summaries (these might contain interest indicators)
            for source, summary in search_summaries.items():
                if summary and isinstance(summary, str):
                    interest_keywords = self._extract_keywords_from_text(summary)
                    enhanced_interests['keywords'].extend(interest_keywords)
            
            # If there are extracted interests in the data
            interests_data = personalization_data.get('interests', [])
            if interests_data:
                for interest_item in interests_data:
                    if isinstance(interest_item, dict):
                        category = interest_item.get('category', '')
                        confidence = interest_item.get('confidence', 0.5)
                        keywords = interest_item.get('keywords', [])
                        
                        if category and category not in enhanced_interests['categories']:
                            enhanced_interests['categories'].append(category)
                            enhanced_interests['category_scores'][category] = confidence
                            enhanced_interests['keywords'].extend(keywords)
        
        # Extract keywords from activity description
        if activity:
            activity_keywords = self._extract_keywords_from_text(activity)
            enhanced_interests['activity_keywords'] = activity_keywords
            enhanced_interests['keywords'].extend(activity_keywords)
        
        # Remove duplicates
        enhanced_interests['keywords'] = list(set(enhanced_interests['keywords']))
        enhanced_interests['categories'] = list(set(enhanced_interests['categories']))
        
        logger.info(f"Enhanced interests extracted: {len(enhanced_interests['categories'])} categories, "
                   f"{len(enhanced_interests['keywords'])} keywords")
        
        return enhanced_interests
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract relevant keywords from text content"""
        if not text:
            return []
        
        # Simple keyword extraction - can be enhanced with NLP libraries
        import re
        
        # Define interest-related keywords
        interest_keywords = {
            'music': ['music', 'concert', 'band', 'singer', 'album', 'song', 'artist', 'festival', 'show', 'performance'],
            'sports': ['sport', 'game', 'team', 'fitness', 'exercise', 'basketball', 'football', 'soccer', 'tennis', 'golf'],
            'arts': ['art', 'theater', 'museum', 'gallery', 'dance', 'exhibition', 'culture', 'painting', 'sculpture'],
            'food': ['food', 'restaurant', 'cooking', 'cuisine', 'chef', 'dining', 'culinary', 'recipe', 'meal'],
            'technology': ['tech', 'programming', 'code', 'software', 'computer', 'digital', 'innovation', 'startup'],
            'entertainment': ['movie', 'film', 'tv', 'show', 'entertainment', 'comedy', 'drama', 'cinema'],
            'nature': ['nature', 'outdoor', 'hiking', 'camping', 'park', 'beach', 'environment', 'eco'],
            'social': ['community', 'social', 'networking', 'meetup', 'group', 'volunteer', 'charity'],
            'education': ['education', 'learning', 'workshop', 'seminar', 'course', 'training', 'lecture'],
            'business': ['business', 'networking', 'entrepreneur', 'startup', 'conference', 'professional']
        }
        
        text_lower = text.lower()
        found_keywords = []
        
        for category, keywords in interest_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append(keyword)
        
        return found_keywords
    
    def _search_by_enhanced_interests(self, latitude: float, longitude: float, 
                                    enhanced_interests: Dict[str, Any], activity: str) -> List[Event]:
        """Search for events based on enhanced interest profile"""
        events = []
        
        # Map enhanced interests to Ticketmaster categories
        category_mapping = {
            'music': 'music',
            'sports': 'sports', 
            'theater': 'arts',
            'arts': 'arts',
            'comedy': 'arts',
            'family': 'family',
            'food': 'miscellaneous',
            'fitness': 'sports',
            'technology': 'miscellaneous',
            'entertainment': 'arts',
            'nature': 'miscellaneous',
            'social': 'miscellaneous',
            'education': 'miscellaneous',
            'business': 'miscellaneous'
        }
        
        # Get categories with confidence scores
        search_categories = []
        category_scores = enhanced_interests.get('category_scores', {})
        
        for category in enhanced_interests.get('categories', []):
            tm_category = category_mapping.get(category.lower())
            if tm_category and tm_category not in search_categories:
                search_categories.append(tm_category)
        
        # If no categories from interests, try to derive from keywords
        if not search_categories and enhanced_interests.get('keywords'):
            keywords_text = ' '.join(enhanced_interests['keywords'])
            search_categories = self._categorize_activity_with_ai(keywords_text)
        
        # If still no categories, use activity
        if not search_categories and activity:
            search_categories = self._categorize_activity_with_ai(activity)
        
        # Fallback to default categories
        if not search_categories:
            search_categories = self.config.get('DEFAULT_CATEGORIES', ['music', 'sports', 'arts'])
        
        # Search for each category with keyword filtering
        for category in search_categories:
            try:
                params = {
                    'apikey': self.api_key,
                    'latlong': f"{latitude},{longitude}",
                    'radius': self.config.get('SEARCH_RADIUS', 50),
                    'unit': 'miles',
                    'size': 15,  # Get more results for better filtering
                    'sort': 'date,asc',
                    'classificationName': category
                }
                
                # Add keyword filtering if available
                keywords = enhanced_interests.get('keywords', [])
                activity_keywords = enhanced_interests.get('activity_keywords', [])
                all_keywords = keywords + activity_keywords
                
                if all_keywords:
                    # Use most relevant keywords for search
                    top_keywords = all_keywords[:3]  # Limit to avoid too restrictive search
                    keyword_query = ' OR '.join(top_keywords)
                    params['keyword'] = keyword_query
                
                response = self._make_request('/events.json', params)
                if response and '_embedded' in response:
                    category_events = self._parse_events(response['_embedded']['events'])
                    events.extend(category_events)
                    
            except Exception as e:
                logger.error(f"Error searching events for enhanced category {category}: {e}")
                continue
        
        return events
    
    def _filter_and_rank_events(self, events: List[Event], enhanced_interests: Dict[str, Any], 
                               personalization_data: Dict[str, Any]) -> List[Event]:
        """
        Filter and rank events based on enhanced user profile using AI analysis
        
        Args:
            events: List of events to filter and rank
            enhanced_interests: Enhanced interest data
            personalization_data: Full personalization data
            
        Returns:
            Filtered and ranked events with relevance scores and AI recommendations
        """
        if not events:
            return events
        
        # Use AI to intelligently rank events
        events = self._ai_rank_events(events, enhanced_interests, personalization_data)
        
        # Apply traditional scoring as backup/boost
        events = self._apply_traditional_scoring(events, enhanced_interests)
        
        # Filter out events with very low relevance
        min_relevance = self.config.get('MIN_RELEVANCE_SCORE', 0.15)
        filtered_events = [event for event in events if getattr(event, 'relevance_score', 0) >= min_relevance]
        
        logger.info(f"AI-filtered {len(events)} events down to {len(filtered_events)} relevant events")
        
        return filtered_events
    
    def _ai_rank_events(self, events: List[Event], enhanced_interests: Dict[str, Any], 
                       personalization_data: Dict[str, Any]) -> List[Event]:
        """Use OpenAI to intelligently rank events based on user profile and activity request"""
        try:
            from config.settings import OPENAI_API_KEY
            if not OPENAI_API_KEY or len(events) == 0:
                return events
            
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            # Extract user context
            user_activity = personalization_data.get('activity', '') if personalization_data else ''
            user_interests = enhanced_interests.get('categories', [])
            user_keywords = enhanced_interests.get('keywords', [])
            activity_keywords = enhanced_interests.get('activity_keywords', [])
            
            # Get user profile data if available
            user_profile_data = personalization_data.get('user_profile', {}) if personalization_data else {}
            preferences = user_profile_data.get('preferences', {})
            behavioral_patterns = user_profile_data.get('behavioral_patterns', {})
            activity_context = user_profile_data.get('activity_context', {})
            
            # Create event summaries for AI analysis
            event_summaries = []
            for i, event in enumerate(events[:15]):  # Limit to top 15 events to avoid token limits
                event_summary = {
                    'index': i,
                    'name': event.name,
                    'category': event.category,
                    'subcategory': event.subcategory,
                    'venue': event.venue,
                    'date': event.date,
                    'time': event.time,
                    'description': event.description[:200] if event.description else '',
                    'price_min': event.price_min,
                    'price_max': event.price_max
                }
                event_summaries.append(event_summary)
            
            # Create comprehensive prompt for AI analysis
            prompt = self._create_ai_ranking_prompt(
                user_activity, user_interests, user_keywords, activity_keywords,
                preferences, behavioral_patterns, activity_context, event_summaries
            )
            
            # Get AI ranking
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert event recommendation AI. Analyze user profiles and rank events based on relevance to their specific activity request and interests."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse AI response and apply scores
            ai_rankings = self._parse_ai_rankings(response.choices[0].message.content)
            events = self._apply_ai_rankings(events, ai_rankings)
            
            logger.info(f"AI ranking completed for {len(events)} events")
            
        except Exception as e:
            logger.warning(f"AI ranking failed, falling back to traditional scoring: {e}")
        
        return events
    
    def _create_ai_ranking_prompt(self, user_activity: str, user_interests: List[str], 
                                 user_keywords: List[str], activity_keywords: List[str],
                                 preferences: Dict[str, Any], behavioral_patterns: Dict[str, Any],
                                 activity_context: Dict[str, Any], event_summaries: List[Dict]) -> str:
        """Create a comprehensive prompt for AI event ranking"""
        
        prompt = f"""
You are helping a user find the most relevant events based on their specific request and profile.

USER'S ACTIVITY REQUEST: "{user_activity}"

USER PROFILE:
- Primary Interests: {', '.join(user_interests) if user_interests else 'None specified'}
- Interest Keywords: {', '.join(user_keywords) if user_keywords else 'None'}
- Activity Keywords: {', '.join(activity_keywords) if activity_keywords else 'None'}

PREFERENCES:
- Preferred Categories: {preferences.get('preferred_categories', [])}
- Social Preference: {preferences.get('social_preference', 'flexible')}
- Activity Style: {preferences.get('activity_style', 'balanced')}
- Budget Preference: {preferences.get('budget_preference', 'medium')}
- Preferred Time: {preferences.get('preferred_time', 'flexible')}

BEHAVIORAL PATTERNS:
- Adventure Seeking: {behavioral_patterns.get('adventure_seeker', 0):.2f}
- Social Learning: {behavioral_patterns.get('social_learner', 0):.2f}
- Creative Expression: {behavioral_patterns.get('creative_expression', 0):.2f}
- Learning Oriented: {behavioral_patterns.get('learning_oriented', 0):.2f}

ACTIVITY CONTEXT:
- Intent: {activity_context.get('intent', 'unknown')}
- Urgency: {activity_context.get('urgency', 'medium')}
- Social Setting: {activity_context.get('social_setting', 'flexible')}
- Budget Preference: {activity_context.get('budget_preference', 'medium')}

AVAILABLE EVENTS:
"""
        
        for event in event_summaries:
            price_info = ""
            if event['price_min'] is not None:
                if event['price_max'] and event['price_max'] != event['price_min']:
                    price_info = f" (${event['price_min']}-${event['price_max']})"
                else:
                    price_info = f" (${event['price_min']})"
            elif event['price_min'] == 0 or event['price_min'] is None:
                price_info = " (Free/TBD)"
            
            prompt += f"""
{event['index']}. {event['name']}
   Category: {event['category']} | {event['subcategory']}
   Date/Time: {event['date']} at {event['time']}
   Venue: {event['venue']}{price_info}
   Description: {event['description']}
"""
        
        prompt += f"""

TASK:
Rank these events from 0-10 based on how well they match:
1. The user's specific activity request: "{user_activity}"
2. Their interests and behavioral patterns
3. Their preferences and context

Focus heavily on what the user actually said they want to do that day.

Provide your response as a JSON array with this format:
[
  {{"index": 0, "score": 8.5, "reason": "Perfect match for user's request because..."}},
  {{"index": 1, "score": 7.2, "reason": "Good fit because..."}},
  ...
]

Only include events with scores 5.0 or higher. Sort by score (highest first).
"""
        
        return prompt
    
    def _parse_ai_rankings(self, ai_response: str) -> Dict[int, Dict[str, Any]]:
        """Parse AI ranking response into usable format"""
        rankings = {}
        
        try:
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\[.*?\]', ai_response, re.DOTALL)
            if json_match:
                rankings_data = json.loads(json_match.group())
                
                for item in rankings_data:
                    if isinstance(item, dict) and 'index' in item and 'score' in item:
                        index = item['index']
                        rankings[index] = {
                            'score': float(item['score']),
                            'reason': item.get('reason', ''),
                            'ai_confidence': 0.9
                        }
            
        except Exception as e:
            logger.warning(f"Failed to parse AI rankings: {e}")
        
        return rankings
    
    def _apply_ai_rankings(self, events: List[Event], ai_rankings: Dict[int, Dict[str, Any]]) -> List[Event]:
        """Apply AI rankings to events"""
        for i, event in enumerate(events):
            if i in ai_rankings:
                ranking = ai_rankings[i]
                # Convert AI score (0-10) to relevance score (0-1)
                ai_score = ranking['score'] / 10.0
                
                # Set relevance score and metadata
                setattr(event, 'relevance_score', ai_score)
                setattr(event, 'recommendation_reason', ranking['reason'])
                
                # Update personalization factors
                if not hasattr(event, 'personalization_factors'):
                    setattr(event, 'personalization_factors', {})
                
                event.personalization_factors.update({
                    'ai_score': ai_score,
                    'ai_confidence': ranking['ai_confidence'],
                    'ai_reason': ranking['reason']
                })
            else:
                # Default score for events not ranked by AI
                setattr(event, 'relevance_score', 0.3)
        
        return events
    
    def _apply_traditional_scoring(self, events: List[Event], enhanced_interests: Dict[str, Any]) -> List[Event]:
        """Apply traditional scoring as backup and boost for AI scores"""
        keywords = enhanced_interests.get('keywords', [])
        categories = enhanced_interests.get('categories', [])
        category_scores = enhanced_interests.get('category_scores', {})
        
        for event in events:
            current_score = getattr(event, 'relevance_score', 0.0)
            traditional_boost = 0.0
            
            # Category match bonus
            event_category = event.category.lower()
            if event_category in [cat.lower() for cat in categories]:
                category_confidence = max([category_scores.get(cat, 0.5) for cat in categories 
                                         if cat.lower() == event_category])
                traditional_boost += category_confidence * 0.2
            
            # Keyword matching boost
            event_text = f"{event.name} {event.description} {event.subcategory}".lower()
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in event_text)
            
            if keywords and keyword_matches > 0:
                keyword_score = (keyword_matches / len(keywords)) * 0.15
                traditional_boost += keyword_score
            
            # Time preference boost
            try:
                from datetime import datetime
                event_date = datetime.strptime(event.date, '%Y-%m-%d')
                days_ahead = (event_date - datetime.now()).days
                
                if 0 <= days_ahead <= 7:  # This week
                    traditional_boost += 0.1
                elif 0 <= days_ahead <= 30:  # This month
                    traditional_boost += 0.05
                    
            except (ValueError, AttributeError):
                pass
            
            # Free events boost
            if event.price_min is None or event.price_min == 0:
                traditional_boost += 0.05
            
            # Apply boost to current score
            final_score = min(current_score + traditional_boost, 1.0)
            setattr(event, 'relevance_score', final_score)
        
        return events
    
    def _init_category_mapper(self) -> Dict[str, Dict[str, Any]]:
        """Initialize enhanced category mapping with subcategories and attributes"""
        return {
            'music': {
                'tm_categories': ['music'],
                'subcategories': {
                    'rock': ['rock', 'alternative', 'indie', 'punk'],
                    'pop': ['pop', 'mainstream', 'dance'],
                    'electronic': ['electronic', 'edm', 'techno', 'house'],
                    'jazz': ['jazz', 'blues', 'swing'],
                    'classical': ['classical', 'orchestra', 'symphony'],
                    'country': ['country', 'folk', 'americana'],
                    'hip-hop': ['hip-hop', 'rap', 'urban'],
                    'festival': ['festival', 'multi-day', 'outdoor']
                },
                'venue_types': ['concert hall', 'arena', 'club', 'festival ground', 'theater'],
                'keywords': ['concert', 'live music', 'band', 'artist', 'album', 'tour']
            },
            'sports': {
                'tm_categories': ['sports'],
                'subcategories': {
                    'team_sports': ['football', 'basketball', 'baseball', 'soccer', 'hockey'],
                    'individual': ['tennis', 'golf', 'boxing', 'mma', 'wrestling'],
                    'outdoor': ['cycling', 'running', 'triathlon', 'skiing'],
                    'motorsports': ['racing', 'formula', 'nascar', 'motorcycle']
                },
                'venue_types': ['stadium', 'arena', 'court', 'field', 'track'],
                'keywords': ['game', 'match', 'championship', 'tournament', 'league']
            },
            'arts': {
                'tm_categories': ['arts', 'theatre'],
                'subcategories': {
                    'theater': ['play', 'musical', 'drama', 'comedy'],
                    'dance': ['ballet', 'contemporary', 'cultural'],
                    'visual': ['exhibition', 'gallery', 'museum'],
                    'comedy': ['stand-up', 'improv', 'sketch']
                },
                'venue_types': ['theater', 'gallery', 'museum', 'arts center'],
                'keywords': ['performance', 'exhibition', 'show', 'cultural', 'artistic']
            },
            'family': {
                'tm_categories': ['family'],
                'subcategories': {
                    'kids': ['children', 'family-friendly', 'educational'],
                    'entertainment': ['circus', 'magic', 'puppet'],
                    'seasonal': ['holiday', 'christmas', 'halloween']
                },
                'venue_types': ['family center', 'park', 'indoor venue'],
                'keywords': ['family', 'kids', 'children', 'all ages']
            },
            'miscellaneous': {
                'tm_categories': ['miscellaneous'],
                'subcategories': {
                    'food': ['food festival', 'wine tasting', 'culinary'],
                    'technology': ['tech conference', 'startup', 'innovation'],
                    'health': ['wellness', 'fitness', 'yoga'],
                    'business': ['networking', 'conference', 'professional']
                },
                'venue_types': ['conference center', 'convention hall', 'outdoor space'],
                'keywords': ['festival', 'expo', 'conference', 'workshop']
            }
        }
    
    def _init_preference_analyzer(self) -> Dict[str, Any]:
        """Initialize preference analysis patterns"""
        return {
            'time_preferences': {
                'morning': {'keywords': ['morning', 'early', 'breakfast', 'sunrise'], 'hours': [6, 7, 8, 9, 10, 11]},
                'afternoon': {'keywords': ['afternoon', 'lunch', 'midday'], 'hours': [12, 13, 14, 15, 16, 17]},
                'evening': {'keywords': ['evening', 'dinner', 'night', 'sunset'], 'hours': [18, 19, 20, 21, 22]},
                'late_night': {'keywords': ['late', 'midnight', 'after hours'], 'hours': [23, 0, 1, 2]}
            },
            'price_sensitivity': {
                'budget': {'keywords': ['cheap', 'free', 'budget', 'affordable'], 'max_price': 25},
                'moderate': {'keywords': ['reasonable', 'fair', 'moderate'], 'max_price': 75},
                'premium': {'keywords': ['premium', 'luxury', 'high-end', 'exclusive'], 'max_price': None}
            },
            'venue_preferences': {
                'intimate': {'keywords': ['small', 'intimate', 'cozy', 'close'], 'capacity': 500},
                'medium': {'keywords': ['medium', 'moderate', 'comfortable'], 'capacity': 2000},
                'large': {'keywords': ['big', 'arena', 'stadium', 'massive'], 'capacity': None}
            }
        }
    
    def _init_behavioral_filter(self) -> Dict[str, Dict[str, Any]]:
        """Initialize behavioral filtering patterns"""
        return {
            'social_preference': {
                'solo': {
                    'boost_categories': ['arts', 'education', 'cultural'],
                    'avoid_categories': ['party', 'festival'],
                    'venue_preference': 'intimate'
                },
                'group': {
                    'boost_categories': ['music', 'sports', 'festival'],
                    'avoid_categories': ['meditation', 'lecture'],
                    'venue_preference': 'large'
                },
                'family': {
                    'boost_categories': ['family', 'educational', 'cultural'],
                    'filter_content': True,
                    'time_preference': 'afternoon'
                }
            },
            'activity_style': {
                'adventurous': {
                    'boost_keywords': ['new', 'unique', 'extreme', 'adventure', 'outdoor'],
                    'avoid_keywords': ['traditional', 'classic', 'routine']
                },
                'educational': {
                    'boost_keywords': ['learn', 'workshop', 'lecture', 'educational', 'cultural'],
                    'boost_categories': ['arts', 'miscellaneous']
                },
                'creative': {
                    'boost_keywords': ['creative', 'artistic', 'hands-on', 'workshop', 'exhibition'],
                    'boost_categories': ['arts']
                }
            },
            'lifestyle': {
                'active': {
                    'boost_categories': ['sports', 'outdoor'],
                    'boost_keywords': ['fitness', 'active', 'outdoor', 'physical']
                },
                'cultural': {
                    'boost_categories': ['arts', 'music'],
                    'boost_keywords': ['cultural', 'artistic', 'performance', 'exhibition']
                },
                'social': {
                    'boost_keywords': ['social', 'networking', 'community', 'group']
                }
            }
        }
