"""
Mapping service for interactive event visualization

This module manages map markers, event categorization, and geographical data
for the interactive map interface. Supports filtering, searching, and real-time
event display with category-based organization and statistics.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class MapMarker:
    """Map marker data structure"""
    id: str
    name: str
    latitude: float
    longitude: float
    category: str
    subcategory: str = ""
    description: str = ""
    url: str = ""
    date: str = ""
    time: str = ""
    venue: str = ""
    address: str = ""
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    image_url: str = ""
    source: str = "unknown"  # ticketmaster, eventbrite, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert marker to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'category': self.category,
            'subcategory': self.subcategory,
            'description': self.description,
            'url': self.url,
            'date': self.date,
            'time': self.time,
            'venue': self.venue,
            'address': self.address,
            'price_min': self.price_min,
            'price_max': self.price_max,
            'image_url': self.image_url,
            'source': self.source
        }


class MappingService:
    """Service for aggregating events from multiple APIs and displaying on a map"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize mapping service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.markers = []
        
    def clear_markers(self):
        """Clear all markers"""
        self.markers = []
    
    def add_ticketmaster_events(self, events: List[Any]):
        """Add events from Ticketmaster to the map"""
        for event in events:
            marker = MapMarker(
                id=f"tm_{event.id}",
                name=event.name,
                latitude=event.latitude,
                longitude=event.longitude,
                category=event.category,
                subcategory=event.subcategory,
                description=event.description,
                url=event.url,
                date=event.date,
                time=event.time,
                venue=event.venue,
                address=event.address,
                price_min=event.price_min,
                price_max=event.price_max,
                image_url=event.image_url,
                source="ticketmaster"
            )
            self.markers.append(marker)
    
    def add_allevents_events(self, events: List[Any]):
        """Add events from AllEvents to the map"""
        for event in events:
            marker = MapMarker(
                id=f"ae_{event.id}",
                name=event.name,
                latitude=event.latitude,
                longitude=event.longitude,
                category=event.category,
                subcategory=event.subcategory,
                description=event.description,
                url=event.url,
                date=event.date,
                time=event.time,
                venue=event.venue,
                address=event.address,
                price_min=event.price_min,
                price_max=event.price_max,
                image_url=event.image_url,
                source="allevents"
            )
            self.markers.append(marker)
    
    def add_unified_events(self, events: List[Any]):
        """Add events from unified events to the map"""
        for event in events:
            marker = MapMarker(
                id=f"ue_{event.id}",
                name=event.name,
                latitude=event.latitude,
                longitude=event.longitude,
                category=event.category,
                subcategory=event.subcategory,
                description=event.description,
                url=event.url,
                date=event.date,
                time=event.time,
                venue=event.venue,
                address=event.address,
                price_min=event.price_min,
                price_max=event.price_max,
                image_url=event.image_url,
                source="unifiedevents"
            )
            self.markers.append(marker)

    def add_eventbrite_events(self, events: List[Dict[str, Any]]):
        """Add events from Eventbrite to the map (placeholder for future integration)"""
        for event in events:
            try:
                marker = MapMarker(
                    id=f"eb_{event.get('id', '')}",
                    name=event.get('name', {}).get('text', 'Unknown Event'),
                    latitude=float(event.get('venue', {}).get('latitude', 0)),
                    longitude=float(event.get('venue', {}).get('longitude', 0)),
                    category=event.get('category', 'miscellaneous'),
                    description=event.get('description', {}).get('text', ''),
                    url=event.get('url', ''),
                    date=event.get('start', {}).get('local', '').split('T')[0],
                    time=event.get('start', {}).get('local', '').split('T')[1] if 'T' in event.get('start', {}).get('local', '') else '',
                    venue=event.get('venue', {}).get('name', ''),
                    address=event.get('venue', {}).get('address', {}).get('localized_address_display', ''),
                    source="eventbrite"
                )
                
                if marker.latitude and marker.longitude:
                    self.markers.append(marker)
                    
            except Exception as e:
                logger.warning(f"Failed to parse Eventbrite event: {e}")
                continue
    
    def add_meetup_events(self, events: List[Dict[str, Any]]):
        """Add events from Meetup to the map (placeholder for future integration)"""
        for event in events:
            try:
                venue = event.get('venue', {})
                marker = MapMarker(
                    id=f"mu_{event.get('id', '')}",
                    name=event.get('name', 'Unknown Event'),
                    latitude=float(venue.get('lat', 0)),
                    longitude=float(venue.get('lon', 0)),
                    category='meetup',
                    description=event.get('description', ''),
                    url=event.get('link', ''),
                    date=event.get('local_date', ''),
                    time=event.get('local_time', ''),
                    venue=venue.get('name', ''),
                    address=venue.get('address_1', ''),
                    source="meetup"
                )
                
                if marker.latitude and marker.longitude:
                    self.markers.append(marker)
                    
            except Exception as e:
                logger.warning(f"Failed to parse Meetup event: {e}")
                continue
    
    def add_custom_locations(self, locations: List[Dict[str, Any]]):
        """Add custom locations to the map"""
        for location in locations:
            try:
                marker = MapMarker(
                    id=f"custom_{location.get('id', len(self.markers))}",
                    name=location.get('name', 'Custom Location'),
                    latitude=float(location.get('latitude', 0)),
                    longitude=float(location.get('longitude', 0)),
                    category=location.get('category', 'custom'),
                    description=location.get('description', ''),
                    url=location.get('url', ''),
                    address=location.get('address', ''),
                    source="custom"
                )
                
                if marker.latitude and marker.longitude:
                    self.markers.append(marker)
                    
            except Exception as e:
                logger.warning(f"Failed to parse custom location: {e}")
                continue
    
    def get_markers_by_category(self, category: str) -> List[MapMarker]:
        """Get all markers for a specific category"""
        return [marker for marker in self.markers if marker.category.lower() == category.lower()]
    
    def get_markers_by_source(self, source: str) -> List[MapMarker]:
        """Get all markers from a specific source"""
        return [marker for marker in self.markers if marker.source.lower() == source.lower()]
    
    def get_all_markers(self) -> List[MapMarker]:
        """Get all markers"""
        return self.markers
    
    def get_map_data(self, center_lat: float, center_lng: float) -> Dict[str, Any]:
        """
        Get map data for frontend display
        
        Args:
            center_lat: Center latitude for the map
            center_lng: Center longitude for the map
            
        Returns:
            Dictionary containing map configuration and markers
        """
        # Limit markers for performance
        max_markers = self.config.get('MAX_MARKERS', 50)
        limited_markers = self.markers[:max_markers]
        
        # Group markers by category for better organization
        categories = {}
        for marker in limited_markers:
            category = marker.category
            if category not in categories:
                categories[category] = []
            categories[category].append(marker.to_dict())
        
        return {
            'center': {
                'latitude': center_lat,
                'longitude': center_lng
            },
            'zoom': self.config.get('DEFAULT_ZOOM', 12),
            'markers': [marker.to_dict() for marker in limited_markers],
            'categories': categories,
            'total_markers': len(self.markers),
            'sources': list(set(marker.source for marker in self.markers)),
            'tile_server': self.config.get('TILE_SERVER', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
            'attribution': self.config.get('ATTRIBUTION', '&copy; OpenStreetMap contributors')
        }
    
    def get_category_stats(self) -> Dict[str, int]:
        """Get statistics about markers by category"""
        stats = {}
        for marker in self.markers:
            category = marker.category
            stats[category] = stats.get(category, 0) + 1
        return stats
    
    def filter_markers_by_distance(self, center_lat: float, center_lng: float, 
                                 max_distance_km: float) -> List[MapMarker]:
        """
        Filter markers by distance from a center point
        
        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            max_distance_km: Maximum distance in kilometers
            
        Returns:
            List of markers within the specified distance
        """
        import math
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate the haversine distance between two points"""
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        
        filtered_markers = []
        for marker in self.markers:
            distance = haversine_distance(
                center_lat, center_lng,
                marker.latitude, marker.longitude
            )
            if distance <= max_distance_km:
                filtered_markers.append(marker)
        
        return filtered_markers
    
    def search_markers(self, query: str) -> List[MapMarker]:
        """
        Search markers by name, description, or venue
        
        Args:
            query: Search query string
            
        Returns:
            List of matching markers
        """
        query_lower = query.lower()
        matching_markers = []
        
        for marker in self.markers:
            if (query_lower in marker.name.lower() or
                query_lower in marker.description.lower() or
                query_lower in marker.venue.lower() or
                query_lower in marker.category.lower()):
                matching_markers.append(marker)
        
        return matching_markers
