"""
Geocoding service for location handling

This module provides location services using OpenStreetMap's Nominatim API,
including reverse geocoding for converting coordinates to address information.
Privacy-focused implementation with configurable timeouts and user agents.
"""
import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for handling geocoding operations"""
    
    def __init__(self, user_agent: str = "WhatNowAI/1.0"):
        """
        Initialize geocoding service
        
        Args:
            user_agent: User agent string for API requests
        """
        self.user_agent = user_agent
        self.base_url = "https://nominatim.openstreetmap.org/reverse"
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Reverse geocode coordinates to address information
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dictionary with location information or None if failed
        """
        try:
            params = {
                'format': 'json',
                'lat': latitude,
                'lon': longitude,
                'zoom': 18,
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            response = requests.get(
                self.base_url, 
                params=params, 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                geo_data = response.json()
                return self._extract_location_info(geo_data, latitude, longitude)
            else:
                logger.error(f"Geocoding API returned status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Geocoding request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    def _extract_location_info(self, geo_data: Dict, latitude: float, longitude: float) -> Dict:
        """
        Extract relevant location information from geocoding response
        
        Args:
            geo_data: Raw geocoding response
            latitude: Original latitude
            longitude: Original longitude
            
        Returns:
            Cleaned location information dictionary
        """
        address = geo_data.get('address', {})
        
        # Extract city with fallback options
        city = (address.get('city') or 
                address.get('town') or 
                address.get('village') or 
                address.get('hamlet') or 
                'Unknown')
        
        return {
            'country': address.get('country', 'Unknown'),
            'city': city,
            'zipcode': address.get('postcode', 'Unknown'),
            'latitude': latitude,
            'longitude': longitude,
            'full_address': geo_data.get('display_name', 'Unknown')
        }
