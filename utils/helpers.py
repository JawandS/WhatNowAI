"""
Utility functions for data processing
"""
import re
from typing import Dict, Any, Optional


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for better TTS pronunciation
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text suitable for TTS
    """
    if not text:
        return ""
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Remove code
    
    # Replace multiple newlines with periods
    text = re.sub(r'\n\n+', '. ', text)
    text = re.sub(r'\n', '. ', text)
    
    # Clean up multiple periods
    text = re.sub(r'\.{2,}', '.', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """
    Validate latitude and longitude coordinates
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    if latitude is None or longitude is None:
        return False
    
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        # Check if coordinates are in valid range
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return True
        return False
    except (ValueError, TypeError, OverflowError):
        return False


def sanitize_social_handle(handle: str) -> str:
    """
    Sanitize social media handle
    
    Args:
        handle: Raw social media handle
        
    Returns:
        Cleaned handle without @ symbol
    """
    if not handle:
        return ""
    
    # Remove @ symbol and whitespace
    return handle.replace('@', '').strip()


def format_location_string(location_data: Dict[str, Any]) -> str:
    """
    Format location data into a readable string
    
    Args:
        location_data: Dictionary containing location information
        
    Returns:
        Formatted location string
    """
    if not location_data:
        return "Unknown location"
    
    city = location_data.get('city', 'Unknown')
    country = location_data.get('country', 'Unknown')
    zipcode = location_data.get('zipcode', 'Unknown')
    
    location_str = f"{city}, {country}"
    if zipcode != 'Unknown':
        location_str += f" ({zipcode})"
    
    return location_str

