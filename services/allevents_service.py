"""
AllEvents API service for event discovery

This module integrates with the AllEvents API to find local events
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


class AllEventsService:
    """Service for intelligent event discovery from AllEvents API with personalization"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        """
        Initialize AllEvents service
        
        Args:
            api_key: AllEvents API key
            config: Configuration dictionary
        """
        self.api_key = api_key
        self.config = config
        self.base_url = config.get('BASE_URL', 'https://allevents.developer.azure-api.net/api')
        self.session = requests.Session()
        
        # Set default headers for API
        self.session.headers.update({
            'Ocp-Apim-Subscription-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        
    def search_events(self, location: Dict[str, Any], user_interests: List[str] = None, 
                     user_activity: str = "", personalization_data: Dict[str, Any] = None,
                     user_profile: Any = None) -> List[Any]:
        """
        Search for events near a location based on user interests and enhanced personalization
        
        Args:
            location: Dictionary with latitude, longitude, city, country
            user_interests: List of user interest categories
            user_activity: What the user wants to do
            personalization_data: Enhanced personalization data from background search
            user_profile: Enhanced user profile from user_profiling_service
            
        Returns:
            List of Event objects (using same structure as Ticketmaster) filtered and ranked by AI and user preferences
        """
        if not self.api_key:
            logger.warning("AllEvents API key not provided")
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
            logger.error(f"Failed to convert coordinates to float in AllEvents service: {e}")
            return []
        
        if not latitude or not longitude:
            logger.warning("Location coordinates not provided or invalid for AllEvents")
            return []
        
        logger.info(f"Searching AllEvents with AI-enhanced personalization: "
                   f"location=({latitude},{longitude}), "
                   f"basic_interests={user_interests}, "
                   f"activity='{user_activity}', "
                   f"has_personalization_data={bool(personalization_data)}, "
                   f"has_profile={bool(user_profile)}")
        
        events = []
        
        try:
            # Build search parameters
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'radius': 50,  # 50km radius
                'limit': 50,   # Get more events for better filtering
                'sort': 'relevance'
            }
            
            # Add city/location if available
            if city:
                params['city'] = city
            
            # Add date range (next 30 days)
            today = datetime.now()
            end_date = today + timedelta(days=30)
            params['start_date'] = today.strftime('%Y-%m-%d')
            params['end_date'] = end_date.strftime('%Y-%m-%d')
            
            # Add categories based on user interests and activity
            categories = self._map_interests_to_categories(user_interests, user_activity, user_profile)
            if categories:
                params['categories'] = ','.join(categories)
            
            logger.info(f"AllEvents API request params: {params}")
            
            # Make API request
            response = self.session.get(
                f"{self.base_url}/events/search",
                params=params,
                timeout=self.config.get('TIMEOUT', 10)
            )
            
            if response.status_code == 200:
                data = response.json()
                raw_events = data.get('events', [])
                
                logger.info(f"AllEvents API returned {len(raw_events)} raw events")
                
                # Convert to our Event format
                for event_data in raw_events:
                    try:
                        event = self._convert_to_event_format(event_data, location)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to convert AllEvents event: {e}")
                        continue
                
                logger.info(f"Successfully converted {len(events)} AllEvents events")
                
                # Apply AI-powered filtering and ranking
                if user_profile and events:
                    events = self._apply_ai_filtering(events, user_profile, user_activity, personalization_data)
                
            else:
                logger.error(f"AllEvents API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"AllEvents API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in AllEvents search: {e}")
        
        return events
    
    def _map_interests_to_categories(self, user_interests: List[str], user_activity: str, user_profile: Any) -> List[str]:
        """Map user interests and activities to AllEvents categories"""
        category_mapping = {
            # Music and Entertainment
            'music': ['music', 'concerts', 'festivals'],
            'concerts': ['music', 'concerts'],
            'festivals': ['festivals', 'music', 'food'],
            'nightlife': ['nightlife', 'parties'],
            'comedy': ['comedy', 'entertainment'],
            'theatre': ['theatre', 'performing-arts'],
            'entertainment': ['entertainment', 'performing-arts'],
            
            # Sports and Fitness
            'sports': ['sports', 'fitness'],
            'fitness': ['fitness', 'sports', 'health'],
            'running': ['sports', 'fitness', 'running'],
            'yoga': ['fitness', 'health', 'wellness'],
            'gym': ['fitness', 'health'],
            
            # Arts and Culture
            'art': ['art', 'exhibitions', 'culture'],
            'museums': ['art', 'culture', 'exhibitions'],
            'exhibitions': ['art', 'exhibitions', 'culture'],
            'culture': ['culture', 'art', 'history'],
            'history': ['culture', 'history', 'education'],
            
            # Food and Drink
            'food': ['food', 'restaurants', 'culinary'],
            'restaurants': ['food', 'culinary'],
            'cooking': ['food', 'culinary', 'workshops'],
            'wine': ['food', 'wine', 'culinary'],
            'beer': ['food', 'beer', 'nightlife'],
            
            # Technology and Business
            'technology': ['technology', 'business', 'conferences'],
            'tech': ['technology', 'business'],
            'business': ['business', 'networking', 'conferences'],
            'networking': ['business', 'networking', 'professional'],
            'conferences': ['conferences', 'business', 'education'],
            
            # Outdoor and Nature
            'outdoor': ['outdoor', 'nature', 'adventure'],
            'hiking': ['outdoor', 'nature', 'sports'],
            'nature': ['nature', 'outdoor', 'environment'],
            'adventure': ['adventure', 'outdoor', 'sports'],
            'cycling': ['sports', 'outdoor', 'cycling'],
            
            # Family and Kids
            'family': ['family', 'kids', 'children'],
            'kids': ['kids', 'family', 'children'],
            'children': ['children', 'family', 'kids'],
            
            # Education and Learning
            'education': ['education', 'workshops', 'learning'],
            'workshops': ['workshops', 'education', 'learning'],
            'learning': ['education', 'workshops', 'personal-development'],
            'books': ['education', 'literature', 'culture'],
            
            # Health and Wellness
            'health': ['health', 'wellness', 'fitness'],
            'wellness': ['wellness', 'health', 'mindfulness'],
            'meditation': ['wellness', 'mindfulness', 'health'],
            
            # Community and Social
            'community': ['community', 'social', 'networking'],
            'volunteering': ['community', 'charity', 'social'],
            'charity': ['charity', 'community', 'volunteering']
        }
        
        categories = set()
        
        # Add categories based on user interests
        if user_interests:
            for interest in user_interests:
                interest_lower = interest.lower()
                if interest_lower in category_mapping:
                    categories.update(category_mapping[interest_lower])
        
        # Add categories based on activity text
        if user_activity:
            activity_lower = user_activity.lower()
            for keyword, cats in category_mapping.items():
                if keyword in activity_lower:
                    categories.update(cats)
        
        # Add categories based on enhanced user profile
        if user_profile and hasattr(user_profile, 'get'):
            profile_interests = user_profile.get('interests', [])
            for interest in profile_interests:
                if isinstance(interest, dict):
                    interest_text = interest.get('category', '').lower()
                elif hasattr(interest, 'category'):
                    interest_text = interest.category.lower()
                else:
                    interest_text = str(interest).lower()
                
                if interest_text in category_mapping:
                    categories.update(category_mapping[interest_text])
        
        return list(categories)
    
    def _convert_to_event_format(self, event_data: Dict[str, Any], location: Dict[str, Any]) -> Any:
        """Convert AllEvents API response to our standard Event format"""
        try:
            # Import Event class from ticketmaster_service to maintain consistency
            from services.ticketmaster_service import Event
            
            # Extract basic event information
            event_id = str(event_data.get('id', ''))
            name = event_data.get('title', '').strip()
            url = event_data.get('url', '')
            
            # Parse date and time
            start_date = event_data.get('start_date', '')
            start_time = event_data.get('start_time', '')
            
            # Format date and time
            date_str = start_date if start_date else 'TBA'
            time_str = start_time if start_time else 'TBA'
            
            # Venue information
            venue_info = event_data.get('venue', {})
            venue_name = venue_info.get('name', 'TBA')
            venue_address = venue_info.get('address', '')
            
            # Location coordinates
            venue_lat = venue_info.get('latitude')
            venue_lon = venue_info.get('longitude')
            
            # Use provided location as fallback
            if not venue_lat or not venue_lon:
                venue_lat = location.get('latitude', 0.0)
                venue_lon = location.get('longitude', 0.0)
            
            # Convert to float
            try:
                venue_lat = float(venue_lat) if venue_lat else 0.0
                venue_lon = float(venue_lon) if venue_lon else 0.0
            except (ValueError, TypeError):
                venue_lat = float(location.get('latitude', 0.0))
                venue_lon = float(location.get('longitude', 0.0))
            
            # Category mapping
            category = event_data.get('category', 'Other')
            subcategory = event_data.get('subcategory', '')
            
            # Image URL
            image_url = event_data.get('image_url', '')
            if isinstance(event_data.get('images'), list) and event_data['images']:
                image_url = event_data['images'][0].get('url', image_url)
            
            # Description
            description = event_data.get('description', '')
            
            # Note: Removing price information as requested
            # price_min = None
            # price_max = None
            
            # Create Event object
            event = Event(
                id=f"allevents_{event_id}",  # Prefix to distinguish from Ticketmaster
                name=name,
                url=url,
                date=date_str,
                time=time_str,
                venue=venue_name,
                address=venue_address,
                city=location.get('city', ''),
                latitude=venue_lat,
                longitude=venue_lon,
                category=category,
                subcategory=subcategory,
                price_min=None,  # Removed as requested
                price_max=None,  # Removed as requested
                image_url=image_url,
                description=description
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error converting AllEvents event to standard format: {e}")
            logger.error(f"Event data: {event_data}")
            return None
    
    def _apply_ai_filtering(self, events: List[Any], user_profile: Any, user_activity: str, 
                          personalization_data: Dict[str, Any]) -> List[Any]:
        """Apply prompt-focused filtering and ranking to events"""
        try:
            logger.info(f"Applying prompt-focused filtering to {len(events)} AllEvents")
            
            # Calculate relevance scores for each event
            for event in events:
                event.relevance_score = self._calculate_simple_relevance(
                    event, user_profile, user_activity
                )
                
                # Add basic personalization factors
                event.personalization_factors = {
                    'prompt_match': self._calculate_prompt_match(event, user_activity) if user_activity else 0,
                    'activity_match': self._calculate_prompt_match(event, user_activity) if user_activity else 0,  # For compatibility
                    'has_image': bool(getattr(event, 'image_url', '')),
                    'has_description': len(getattr(event, 'description', '')) > 50
                }
                
                # Generate recommendation reason
                event.recommendation_reason = self._generate_recommendation_reason(
                    event, user_activity
                )
            
            # Filter events with flexible threshold
            min_relevance = 0.1
            filtered_events = []
            
            for event in events:
                prompt_score = event.personalization_factors.get('prompt_match', 0)
                overall_score = event.relevance_score
                
                # Keep events with high prompt match OR good overall score
                if prompt_score > 0.25 or overall_score >= min_relevance:
                    filtered_events.append(event)
            
            # Sort by prompt match first, then overall score
            filtered_events.sort(key=lambda x: (
                x.personalization_factors.get('prompt_match', 0),
                x.relevance_score
            ), reverse=True)
            
            # Limit results
            final_events = filtered_events[:20]
            
            logger.info(f"AllEvents prompt-focused filtering: {len(events)} -> {len(filtered_events)} -> {len(final_events)}")
            
            return final_events
                
        except Exception as e:
            logger.warning(f"AllEvents filtering failed, using simple fallback: {e}")
            return events[:20]
    
    def _generate_recommendation_reason(self, event: Any, user_activity: str) -> str:
        """Generate human-readable recommendation reason for AllEvents"""
        try:
            factors = getattr(event, 'personalization_factors', {})
            prompt_score = factors.get('prompt_match', 0)
            
            if prompt_score > 0.6 and user_activity:
                return f"Recommended because it closely matches your request for '{user_activity}'"
            elif prompt_score > 0.3 and user_activity:
                return f"Recommended because it relates to your interest in '{user_activity}'"
            elif user_activity:
                return f"Recommended as it may interest someone looking for '{user_activity}'"
            else:
                return "Recommended based on your location and general interests"
                
        except Exception:
            return "Recommended based on your location"
    
    def _calculate_simple_relevance(self, event: Any, user_profile: Any, user_activity: str) -> float:
        """Calculate prompt-focused relevance score for an event"""
        score = 0.1  # Lower base score to emphasize prompt matching
        
        try:
            # PRIMARY: Activity/prompt matching (60% weight)
            if user_activity:
                prompt_score = self._calculate_prompt_match(event, user_activity)
                score += prompt_score * 0.6
            
            # SECONDARY: Interest matching (25% weight)
            if user_profile and hasattr(user_profile, 'get'):
                interests = user_profile.get('interests', [])
                event_category = getattr(event, 'category', '').lower()
                
                for interest in interests:
                    if isinstance(interest, dict):
                        interest_text = interest.get('category', '').lower()
                    elif hasattr(interest, 'category'):
                        interest_text = interest.category.lower()
                    else:
                        interest_text = str(interest).lower()
                    
                    if interest_text in event_category or event_category in interest_text:
                        score += 0.25
                        break
            
            # QUALITY: Event completeness (15% weight)
            # Prefer events with images and detailed descriptions
            if getattr(event, 'image_url', ''):
                score += 0.08
            
            if len(getattr(event, 'description', '')) > 50:
                score += 0.07
                
        except Exception as e:
            logger.warning(f"Error calculating relevance score: {e}")
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_prompt_match(self, event: Any, user_activity: str) -> float:
        """Calculate how well the event matches the user's activity prompt"""
        try:
            event_name = getattr(event, 'name', '').lower()
            event_description = getattr(event, 'description', '').lower()
            event_category = getattr(event, 'category', '').lower()
            
            event_text = f"{event_name} {event_description} {event_category}"
            user_activity_lower = user_activity.lower()
            
            score = 0.0
            
            # Exact phrase matching
            if user_activity_lower in event_text:
                score += 0.5
            
            # Individual word matching
            activity_words = [word for word in user_activity_lower.split() if len(word) > 2]
            if activity_words:
                matches = 0
                for word in activity_words:
                    if word in event_name:
                        matches += 2  # Title matches are worth more
                    elif word in event_category:
                        matches += 1.5
                    elif word in event_description:
                        matches += 1
                
                score += min(matches / (len(activity_words) * 2), 0.4)
            
            return min(score, 1.0)
            
        except Exception:
            return 0.0
