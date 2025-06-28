"""
Ticketmaster API service for finding events and activities
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
                     user_activity: str = "") -> List[Event]:
        """
        Search for events near a location based on user interests
        
        Args:
            location: Dictionary with latitude, longitude, city, country
            user_interests: List of user interest categories
            user_activity: What the user wants to do
            
        Returns:
            List of Event objects
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
        
        events = []
        
        try:
            # Search for events based on location
            base_events = self._search_by_location(latitude, longitude)
            events.extend(base_events)
            
            # Search for events based on user interests/activity
            if user_interests or user_activity:
                interest_events = self._search_by_interests(latitude, longitude, user_interests, user_activity)
                events.extend(interest_events)
            
            # Remove duplicates based on event ID
            unique_events = {event.id: event for event in events}
            events = list(unique_events.values())
            
            # Sort by date
            events.sort(key=lambda e: e.date)
            
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
