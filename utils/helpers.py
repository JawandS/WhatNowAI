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
    except (ValueError, TypeError):
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


def generate_response_text(name: str, activity: str, location_data: Dict, social_data: Dict) -> str:
    """
    Generate the main response text for user request
    
    Args:
        name: User's name
        activity: User's desired activity
        location_data: Location information
        social_data: Social media information
        
    Returns:
        Formatted response text
    """
    location_str = format_location_string(location_data)
    
    result = f"Great news, {name}! I've analyzed your request to {activity} in {location_str}.\n\n"
    
    # Add social media context if provided
    twitter_handle = sanitize_social_handle(social_data.get('twitter', ''))
    instagram_handle = sanitize_social_handle(social_data.get('instagram', ''))
    
    if twitter_handle or instagram_handle:
        result += f"I noticed you're active on social media"
        if twitter_handle and instagram_handle:
            result += f" (@{twitter_handle} on X, @{instagram_handle} on Instagram)"
        elif twitter_handle:
            result += f" (@{twitter_handle} on X)"
        elif instagram_handle:
            result += f" (@{instagram_handle} on Instagram)"
        result += f". This gives me additional context about your interests!\n\n"
    
    # Add location-specific suggestions
    country = location_data.get('country', 'Unknown')
    result += f"Here are some location-specific suggestions:\n\n" \
              f"1. Start by breaking down '{activity}' into smaller steps\n" \
              f"2. Research local resources in {country} that can help with {activity}\n" \
              f"3. Check for any location-specific requirements or regulations\n" \
              f"4. Set a timeline for completion\n" \
              f"5. Connect with local communities or groups in your area\n\n"
    
    # Add social media suggestions if applicable
    if twitter_handle or instagram_handle:
        result += f"6. Share your {activity} journey on social media to connect with like-minded people\n" \
                 f"7. Follow relevant accounts and hashtags related to {activity}\n\n"
    
    # Add precise location info if available
    latitude = location_data.get('latitude')
    longitude = location_data.get('longitude')
    if validate_coordinates(latitude, longitude):
        result += f"Based on your precise location ({latitude:.4f}, {longitude:.4f}), " \
                 f"I can provide even more targeted recommendations.\n\n"
    
    result += f"Would you like me to help you create a detailed plan specific to your location?"
    
    return result
