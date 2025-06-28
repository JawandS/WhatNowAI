"""
Ticketmaster API service for event discovery

This module integrates with the Ticketmaster Discovery API to find local events
and activities based on user location and interests. Includes event categorization,
filtering, and comprehensive error handling for reliable event discovery.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

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
            'description': self.description
        }


class TicketmasterService:
    """Service for interacting with Ticketmaster API"""
    
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
        
    def search_events(self, location: Dict[str, Any], user_interests: List[str] = None, 
                     user_activity: str = "", personalization_data: Dict[str, Any] = None) -> List[Event]:
        """
        Search for events near a location based on user interests and personalization data
        
        Args:
            location: Dictionary with latitude, longitude, city, country
            user_interests: List of user interest categories
            user_activity: What the user wants to do
            personalization_data: Enhanced personalization data from background search
            
        Returns:
            List of Event objects filtered and ranked by user preferences
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
        
        logger.info(f"Searching events with enhanced personalization: "
                   f"location=({latitude},{longitude}), "
                   f"basic_interests={user_interests}, "
                   f"activity='{user_activity}', "
                   f"has_personalization_data={bool(personalization_data)}")
        
        events = []
        
        try:
            # Extract enhanced interests from personalization data
            enhanced_interests = self._extract_enhanced_interests(personalization_data, user_interests, user_activity)
            
            # Search for events based on location
            base_events = self._search_by_location(latitude, longitude)
            events.extend(base_events)
            
            # Search for events based on enhanced user profile
            if enhanced_interests['categories'] or user_activity:
                interest_events = self._search_by_enhanced_interests(latitude, longitude, enhanced_interests, user_activity)
                events.extend(interest_events)
            
            # Remove duplicates based on event ID
            unique_events = {event.id: event for event in events}
            events = list(unique_events.values())
            
            # Filter and rank events based on personalization
            events = self._filter_and_rank_events(events, enhanced_interests, personalization_data)
            
            # Sort by relevance score (highest first) then by date
            events.sort(key=lambda e: (-getattr(e, 'relevance_score', 0), e.date))
            
            # Limit results
            max_events = self.config.get('MAX_EVENTS', 20)
            return events[:max_events]
            
        except Exception as e:
            logger.error(f"Error searching Ticketmaster events: {e}")
            return []
    
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
            
            import openai
            openai.api_key = OPENAI_API_KEY
            
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
            
            response = openai.Completion.create(
                engine="gpt-3.5-turbo-instruct",
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
        Filter and rank events based on enhanced user profile
        
        Args:
            events: List of events to filter and rank
            enhanced_interests: Enhanced interest data
            personalization_data: Full personalization data
            
        Returns:
            Filtered and ranked events with relevance scores
        """
        if not events:
            return events
        
        keywords = enhanced_interests.get('keywords', [])
        categories = enhanced_interests.get('categories', [])
        category_scores = enhanced_interests.get('category_scores', {})
        
        # Score each event
        for event in events:
            relevance_score = 0.0
            
            # Base score for having the event
            relevance_score += 0.1
            
            # Category match bonus
            event_category = event.category.lower()
            if event_category in [cat.lower() for cat in categories]:
                category_confidence = max([category_scores.get(cat, 0.5) for cat in categories 
                                         if cat.lower() == event_category])
                relevance_score += category_confidence * 0.4
            
            # Keyword matching in event name and description
            event_text = f"{event.name} {event.description} {event.subcategory}".lower()
            
            keyword_matches = 0
            for keyword in keywords:
                if keyword.lower() in event_text:
                    keyword_matches += 1
            
            if keywords:
                keyword_score = (keyword_matches / len(keywords)) * 0.3
                relevance_score += keyword_score
            
            # Time preference (favor events in near future)
            try:
                from datetime import datetime, timedelta
                event_date = datetime.strptime(event.date, '%Y-%m-%d')
                days_ahead = (event_date - datetime.now()).days
                
                if 0 <= days_ahead <= 7:  # This week
                    relevance_score += 0.15
                elif 0 <= days_ahead <= 30:  # This month
                    relevance_score += 0.1
                elif days_ahead < 0:  # Past events
                    relevance_score -= 0.2
                    
            except (ValueError, AttributeError):
                pass  # Skip time scoring if date parsing fails
            
            # Price preference (favor free or reasonably priced events)
            if event.price_min is None or event.price_min == 0:
                relevance_score += 0.05  # Free events bonus
            elif event.price_min and event.price_min <= 50:
                relevance_score += 0.02  # Affordable events bonus
            
            # Store the relevance score
            setattr(event, 'relevance_score', relevance_score)
        
        # Filter out events with very low relevance (below threshold)
        min_relevance = self.config.get('MIN_RELEVANCE_SCORE', 0.15)
        filtered_events = [event for event in events if getattr(event, 'relevance_score', 0) >= min_relevance]
        
        logger.info(f"Filtered {len(events)} events down to {len(filtered_events)} relevant events")
        
        return filtered_events
