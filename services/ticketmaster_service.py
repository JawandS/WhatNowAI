"""
Ticketmaster API service for event discovery

This module integrates with the Ticketmaster Discovery API to find local events
and activities based on user location and interests. Includes advanced personalization,
AI-powered event ranking, and comprehensive error handling for intelligent
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
    """Event data structure"""
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
    relevance_score: float = 0.0
    personalization_factors: Dict[str, Any] = None
    recommendation_reason: str = ""
    
    def __post_init__(self):
        if self.personalization_factors is None:
            self.personalization_factors = {}
    
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
            'relevance_score': self.relevance_score,
            'personalization_factors': self.personalization_factors,
            'recommendation_reason': self.recommendation_reason
        }


class TicketmasterService:
    """Service for intelligent event discovery from Ticketmaster API with AI-powered personalization"""
    
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
        
        # Interest to category mapping for better event matching
        self.interest_category_mapping = self._load_interest_mapping()
        
    def _load_interest_mapping(self) -> Dict[str, List[str]]:
        """Load mapping from user interests to Ticketmaster categories"""
        return {
            'music': ['music', 'concerts'],
            'sports': ['sports'],
            'arts': ['arts', 'theatre', 'miscellaneous'],
            'technology': ['miscellaneous', 'conferences'],
            'food': ['miscellaneous'],
            'fitness': ['sports', 'miscellaneous'],
            'learning': ['miscellaneous', 'conferences'],
            'entertainment': ['miscellaneous', 'film'],
            'family': ['family'],
            'culture': ['arts', 'theatre', 'miscellaneous']
        }
    
    def search_events(self, location: Dict[str, Any], user_interests: List[str] = None, 
                     user_activity: str = "", personalization_data: Dict[str, Any] = None,
                     user_profile: Any = None) -> List[Event]:
        """
        Search for events near a location based solely on user activity prompt
        
        Args:
            location: Dictionary with latitude, longitude, city, country
            user_interests: Ignored - no user profiling
            user_activity: What the user wants to do (primary ranking factor)
            personalization_data: Ignored - no personalization
            user_profile: Ignored - no user profiling
            
        Returns:
            List of Event objects ranked by prompt relevance only
        """
        if not self.api_key:
            logger.warning("Ticketmaster API key not provided")
            return []
        
        latitude = location.get('latitude')
        longitude = location.get('longitude')
        city = location.get('city', '')
        country = location.get('country', '')
        
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
            logger.warning("Location coordinates not provided or invalid for Ticketmaster")
            return []
        
        logger.info(f"Searching Ticketmaster with prompt-based ranking: "
                   f"location=({latitude},{longitude}), "
                   f"activity='{user_activity}'")
        
        events = []
        
        # Determine categories to search based only on user activity
        categories_to_search = self._determine_search_categories_from_activity(user_activity)
        
        logger.info(f"Determined search categories from activity: {categories_to_search}")
        
        # Search each category
        for category in categories_to_search:
            try:
                category_events = self._search_category(
                    latitude, longitude, category, city, country
                )
                events.extend(category_events)
                logger.info(f"Found {len(category_events)} events in category: {category}")
                
            except Exception as e:
                logger.error(f"Error searching category {category}: {e}")
                continue
        
        logger.info(f"Total events found: {len(events)}")
        
        # Apply simple prompt-based ranking
        if events:
            events = self._apply_prompt_based_ranking(events, user_activity)
        
        logger.info(f"Final events after prompt ranking: {len(events)}")
        return events
    
    def _determine_search_categories_from_activity(self, user_activity: str) -> List[str]:
        """Determine which Ticketmaster categories to search based only on user activity"""
        categories = set()
        
        # Add categories based on activity keywords only
        if user_activity:
            activity_lower = user_activity.lower()
            for interest, tm_categories in self.interest_category_mapping.items():
                if interest in activity_lower:
                    categories.update(tm_categories)
        
        # Default categories if none found - search broadly
        if not categories:
            categories = {'music', 'sports', 'arts', 'miscellaneous'}
        
        return list(categories)
    
    def _search_category(self, latitude: float, longitude: float, category: str, 
                        city: str, country: str) -> List[Event]:
        """Search events in a specific category"""
        params = {
            'apikey': self.api_key,
            'latlong': f"{latitude},{longitude}",
            'radius': self.config.get('SEARCH_RADIUS', 50),
            'unit': 'miles',
            'size': self.config.get('MAX_EVENTS', 20),
            'sort': 'relevance,desc',
            'classificationName': category
        }
        
        # Add date range (next 30 days)
        start_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        params['startDateTime'] = start_date
        params['endDateTime'] = end_date
        
        try:
            response = self.session.get(
                f"{self.base_url}/events.json",
                params=params,
                timeout=self.config.get('TIMEOUT', 10)
            )
            
            if response.status_code == 200:
                data = response.json()
                events_data = data.get('_embedded', {}).get('events', [])
                
                events = []
                for event_data in events_data:
                    try:
                        event = self._parse_event(event_data, category)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse event: {e}")
                        continue
                
                return events
            else:
                logger.error(f"Ticketmaster API error for category {category}: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ticketmaster API request failed for category {category}: {e}")
            return []
    
    def _parse_event(self, event_data: Dict[str, Any], category: str) -> Optional[Event]:
        """Parse Ticketmaster event data into Event object"""
        try:
            # Basic event info
            event_id = event_data.get('id', '')
            name = event_data.get('name', '').strip()
            url = event_data.get('url', '')
            
            # Date and time
            dates = event_data.get('dates', {})
            start_info = dates.get('start', {})
            date_str = start_info.get('localDate', 'TBA')
            time_str = start_info.get('localTime', 'TBA')
            
            # Venue information
            venues = event_data.get('_embedded', {}).get('venues', [])
            if venues:
                venue = venues[0]
                venue_name = venue.get('name', 'TBA')
                venue_address = venue.get('address', {}).get('line1', '')
                venue_city = venue.get('city', {}).get('name', '')
                
                # Location coordinates
                location = venue.get('location', {})
                venue_lat = float(location.get('latitude', 0))
                venue_lon = float(location.get('longitude', 0))
            else:
                venue_name = 'TBA'
                venue_address = ''
                venue_city = ''
                venue_lat = 0.0
                venue_lon = 0.0
            
            # Category and subcategory
            classifications = event_data.get('classifications', [])
            if classifications:
                classification = classifications[0]
                segment = classification.get('segment', {}).get('name', category)
                genre = classification.get('genre', {}).get('name', '')
                subcategory = genre if genre else ''
            else:
                segment = category
                subcategory = ''
            
            # Images
            images = event_data.get('images', [])
            image_url = ''
            if images:
                # Find the best quality image
                for img in images:
                    if img.get('width', 0) >= 640:  # Prefer higher resolution
                        image_url = img.get('url', '')
                        break
                if not image_url and images:
                    image_url = images[0].get('url', '')
            
            # Price information (removed as requested)
            price_min = None
            price_max = None
            
            # Description/info
            info = event_data.get('info', '')
            please_note = event_data.get('pleaseNote', '')
            description = f"{info} {please_note}".strip()
            
            # Create Event object
            event = Event(
                id=event_id,
                name=name,
                url=url,
                date=date_str,
                time=time_str,
                venue=venue_name,
                address=venue_address,
                city=venue_city,
                latitude=venue_lat,
                longitude=venue_lon,
                category=segment.lower(),
                subcategory=subcategory,
                price_min=price_min,
                price_max=price_max,
                image_url=image_url,
                description=description
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing Ticketmaster event: {e}")
            return None
    
    def _apply_prompt_based_ranking(self, events: List[Event], user_activity: str) -> List[Event]:
        """Apply prompt-based ranking to events"""
        logger.info(f"Applying prompt-based ranking to {len(events)} events")
        
        try:
            # Calculate relevance scores for each event based only on prompt
            for event in events:
                event.relevance_score = self._calculate_prompt_relevance_score(event, user_activity)
                event.recommendation_reason = self._generate_simple_recommendation_reason(
                    event.relevance_score, user_activity
                )
            
            # Filter out low-relevance events
            min_relevance = self.config.get('MIN_RELEVANCE_SCORE', 0.15)
            filtered_events = [e for e in events if e.relevance_score >= min_relevance]
            
            # Sort by relevance score
            filtered_events.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Limit results
            max_events = self.config.get('MAX_EVENTS', 20)
            final_events = filtered_events[:max_events]
            
            logger.info(f"Prompt ranking complete: {len(events)} -> {len(filtered_events)} -> {len(final_events)}")
            
            return final_events
            
        except Exception as e:
            logger.error(f"Prompt ranking failed: {e}")
            # Fallback to simple sorting
            return sorted(events, key=lambda x: x.name)[:20]
    
    def _calculate_prompt_relevance_score(self, event: Event, user_activity: str) -> float:
        """Calculate relevance score based only on how well event matches user's prompt"""
        if not user_activity:
            return 0.5  # Neutral score if no activity specified
        
        try:
            # Only factor: How well the event matches the user's activity request
            activity_score = self._calculate_activity_match(event, user_activity)
            
            # Add a small quality bonus to prefer well-documented events
            quality_bonus = self._calculate_quality_score(event) * 0.1
            
            final_score = min(activity_score + quality_bonus, 1.0)
            return final_score
            
        except Exception as e:
            logger.warning(f"Error calculating prompt relevance score: {e}")
            return 0.5
    
    def _calculate_activity_match(self, event: Event, user_activity: str) -> float:
        """Calculate how well event matches user's stated activity"""
        if not user_activity:
            return 0.0
        
        activity_lower = user_activity.lower()
        event_text = f"{event.name} {event.description} {event.category} {event.subcategory}".lower()
        
        # Direct keyword matching
        activity_words = [word for word in activity_lower.split() if len(word) > 2]
        matches = sum(1 for word in activity_words if word in event_text)
        
        if not activity_words:
            return 0.0
        
        base_score = matches / len(activity_words)
        
        # Boost for exact phrase matches
        if activity_lower in event_text:
            base_score = min(base_score + 0.3, 1.0)
        
        return base_score
    
    def _calculate_interest_match(self, event: Event, user_profile: Any, 
                                personalization_data: Dict[str, Any]) -> float:
        """Calculate how well event matches user's interests"""
        score = 0.0
        
        # Check enhanced personalization data
        if personalization_data and personalization_data.get('enhanced_personalization'):
            enhanced_data = personalization_data['enhanced_personalization']
            interests = enhanced_data.get('interests', [])
            
            for interest in interests:
                interest_category = interest.get('category', '').lower()
                interest_keywords = interest.get('keywords', [])
                confidence = interest.get('confidence', 0)
                
                # Category match
                if interest_category == event.category.lower():
                    score += confidence * 0.5
                
                # Keyword matches
                event_text = f"{event.name} {event.description}".lower()
                keyword_matches = sum(1 for keyword in interest_keywords if keyword in event_text)
                if keyword_matches > 0 and interest_keywords:
                    score += (keyword_matches / len(interest_keywords)) * confidence * 0.3
        
        # Check user profile interests
        if user_profile and hasattr(user_profile, 'get'):
            profile_interests = user_profile.get('interests', [])
            for interest in profile_interests:
                if isinstance(interest, dict):
                    interest_category = interest.get('category', '').lower()
                elif hasattr(interest, 'category'):
                    interest_category = interest.category.lower()
                else:
                    interest_category = str(interest).lower()
                
                if interest_category == event.category.lower():
                    score += 0.4
        
        return min(score, 1.0)
    
    def _calculate_behavioral_match(self, event: Event, user_profile: Any, 
                                  personalization_data: Dict[str, Any]) -> float:
        """Calculate behavioral pattern matching"""
        score = 0.0
        
        if personalization_data and personalization_data.get('enhanced_personalization'):
            enhanced_data = personalization_data['enhanced_personalization']
            behavioral_patterns = enhanced_data.get('behavioral_patterns', {})
            
            # Social vs solo preference
            social_score = behavioral_patterns.get('social_preference', 0)
            solo_score = behavioral_patterns.get('solo_preference', 0)
            
            # Events are generally social, so boost for social preference
            if social_score > solo_score:
                score += 0.3
            
            # Adventure seeking
            adventure_score = behavioral_patterns.get('adventure_seeking', 0)
            if adventure_score > 0.3:
                # Boost outdoor/adventure events
                if any(keyword in event.name.lower() for keyword in ['outdoor', 'adventure', 'extreme', 'festival']):
                    score += 0.2
            
            # Learning orientation
            learning_score = behavioral_patterns.get('learning_oriented', 0)
            if learning_score > 0.3:
                # Boost educational/workshop events
                if any(keyword in event.name.lower() for keyword in ['workshop', 'class', 'seminar', 'conference']):
                    score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_time_preference_match(self, event: Event, user_profile: Any, 
                                       personalization_data: Dict[str, Any]) -> float:
        """Calculate time preference matching"""
        score = 0.5  # Neutral base score
        
        if personalization_data and personalization_data.get('enhanced_personalization'):
            enhanced_data = personalization_data['enhanced_personalization']
            behavioral_patterns = enhanced_data.get('behavioral_patterns', {})
            time_patterns = behavioral_patterns.get('time_patterns', {})
            
            if time_patterns:
                # Check if event time matches user preferences
                event_time = event.time.lower() if event.time != 'TBA' else ''
                
                morning_pref = time_patterns.get('morning', 0)
                evening_pref = time_patterns.get('evening', 0)
                weekend_pref = time_patterns.get('weekend', 0)
                
                # Simple time matching (could be enhanced with actual time parsing)
                if morning_pref > 0.3 and any(indicator in event_time for indicator in ['am', 'morning']):
                    score += 0.3
                elif evening_pref > 0.3 and any(indicator in event_time for indicator in ['pm', 'evening']):
                    score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_social_context_match(self, event: Event, user_profile: Any, 
                                      personalization_data: Dict[str, Any]) -> float:
        """Calculate social context matching"""
        score = 0.5  # Neutral base score
        
        if personalization_data and personalization_data.get('enhanced_personalization'):
            enhanced_data = personalization_data['enhanced_personalization']
            social_context = enhanced_data.get('social_context', {})
            
            # Platform-based preferences
            if social_context.get('visual_oriented'):
                # Boost events with good images
                if event.image_url:
                    score += 0.2
            
            if social_context.get('tech_oriented'):
                # Boost tech-related events
                if event.category.lower() in ['miscellaneous'] and any(
                    keyword in event.name.lower() 
                    for keyword in ['tech', 'digital', 'innovation', 'startup']
                ):
                    score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_quality_score(self, event: Event) -> float:
        """Calculate event quality indicators"""
        score = 0.0
        
        # Has image
        if event.image_url:
            score += 0.3
        
        # Has description
        if event.description and len(event.description) > 20:
            score += 0.3
        
        # Has specific venue (not TBA)
        if event.venue != 'TBA' and event.venue:
            score += 0.2
        
        # Has specific time (not TBA)
        if event.time != 'TBA' and event.time:
            score += 0.2
        
        return score
    
    def _generate_personalization_factors(self, event: Event, user_profile: Any, 
                                        user_activity: str, personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed personalization factors for the event"""
        factors = {}
        
        # Activity matching
        factors['activity_match'] = self._calculate_activity_match(event, user_activity)
        
        # Interest matching
        factors['interest_match'] = self._calculate_interest_match(event, user_profile, personalization_data)
        
        # Behavioral matching
        factors['behavioral_match'] = self._calculate_behavioral_match(event, user_profile, personalization_data)
        
        # Quality score
        factors['quality_score'] = self._calculate_quality_score(event)
        
        # Personalization data availability
        factors['has_enhanced_data'] = bool(personalization_data and personalization_data.get('enhanced_personalization'))
        
        return factors
    
    def _generate_recommendation_reason(self, event: Event, user_profile: Any, user_activity: str) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        factors = event.personalization_factors
        
        if factors.get('activity_match', 0) > 0.7:
            reasons.append(f"closely matches your interest in '{user_activity}'")
        elif factors.get('activity_match', 0) > 0.4:
            reasons.append(f"relates to your interest in '{user_activity}'")
        
        if factors.get('interest_match', 0) > 0.7:
            reasons.append("aligns with your profile interests")
        elif factors.get('interest_match', 0) > 0.4:
            reasons.append("matches some of your interests")
        
        if factors.get('behavioral_match', 0) > 0.6:
            reasons.append("fits your activity preferences")
        
        if factors.get('quality_score', 0) > 0.8:
            reasons.append("has detailed information available")
        
        if factors.get('has_enhanced_data'):
            reasons.append("personalized based on your background")
        
        if not reasons:
            return "recommended based on your location and general interests"
        
        return "Recommended because it " + " and ".join(reasons)
    
    def _generate_simple_recommendation_reason(self, relevance_score: float, user_activity: str) -> str:
        """Generate simple recommendation reason based on relevance score and activity"""
        if relevance_score >= 0.8:
            return f"Highly recommended for your interest in '{user_activity}'"
        elif relevance_score >= 0.6:
            return f"Good match for your interest in '{user_activity}'"
        elif relevance_score >= 0.4:
            return f"Related to your interest in '{user_activity}'"
        elif relevance_score >= 0.2:
            return f"May interest you based on '{user_activity}'"
        else:
            return "Recommended based on your location and general preferences"