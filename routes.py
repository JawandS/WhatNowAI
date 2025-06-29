"""
Flask application routes for WhatNowAI

This module defines all the API endpoints for the WhatNowAI application, including:
- Onboarding flow with TTS integration
- Location services and geocoding
- Event discovery and mapping
- Enhanced background research and personalization
"""
from flask import Blueprint, render_template, request, jsonify, abort, send_file
import logging
from typing import Dict, Any

from services.tts_service import TTSService, get_introduction_text, INTRODUCTION_TEXTS
from services.geocoding_service import GeocodingService
from services.ticketmaster_service import TicketmasterService
from services.allevents_service import AllEventsService
from services.unified_events_service import UnifiedEventsService
from services.mapping_service import MappingService
from services.openai_service import OpenAIService
from utils.helpers import validate_coordinates
from config.settings import (AUDIO_DIR, DEFAULT_TTS_VOICE, TICKETMASTER_API_KEY, ALLEVENTS_API_KEY,
                           TICKETMASTER_CONFIG, ALLEVENTS_CONFIG, MAP_CONFIG)

# User profiling and background search removed - ranking now based solely on user prompt

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize services
tts_service = TTSService(str(AUDIO_DIR), DEFAULT_TTS_VOICE)
geocoding_service = GeocodingService()
ticketmaster_service = TicketmasterService(TICKETMASTER_API_KEY, TICKETMASTER_CONFIG)
allevents_service = AllEventsService(ALLEVENTS_API_KEY, ALLEVENTS_CONFIG)
openai_service = OpenAIService()  # Initialize OpenAI service
unified_events_service = UnifiedEventsService(ticketmaster_service, allevents_service, openai_service)
mapping_service = MappingService(MAP_CONFIG)


@main_bp.route('/')
def home():
    """Render the homepage with the form"""
    return render_template('home.html')


@main_bp.route('/tts/introduction/<step>', methods=['POST'])
def generate_introduction_tts(step: str):
    """Generate TTS for introduction steps"""
    try:
        # Get any location data from request for context
        data = request.get_json() if request.is_json else {}
        location_data = data.get('location')
        
        # Generate dynamic text based on time and location
        text = get_introduction_text(step, location_data)
        
        # Fallback to static text if dynamic generation fails
        if not text:
            text = INTRODUCTION_TEXTS.get(step)
            
        if not text:
            return jsonify({
                'success': False,
                'message': 'Invalid introduction step'
            }), 400
        
        audio_id, audio_path = tts_service.generate_audio_sync(text)
        
        if audio_id:
            return jsonify({
                'success': True,
                'audio_id': audio_id,
                'text': text
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate audio'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating introduction TTS: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while generating audio'
        }), 500


@main_bp.route('/submit', methods=['POST'])
def submit_info():
    """Handle form submission with user's name and activity"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        activity = data.get('activity', '').strip()
        social = data.get('social', {})
        
        if not name or not activity:
            return jsonify({
                'success': False,
                'message': 'Please provide both your name and what you want to do.'
            }), 400
        
        # Process the user input - start background processing
        response_message = f"Hello {name}! I'm processing your request to {activity}. Please wait while I work on this..."
        
        return jsonify({
            'success': True,
            'message': response_message,
            'name': name,
            'activity': activity,
            'social': social,
            'processing': True
        })
    
    except Exception as e:
        logger.error(f"Error in submit_info: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500


@main_bp.route('/process', methods=['POST'])
def process_request():
    """Handle background processing of user request with simplified prompt-based approach"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        activity = data.get('activity', '').strip()
        location_data = data.get('location', {})
        social_data = data.get('social', {})
        
        if not name or not activity:
            return jsonify({
                'success': False,
                'message': 'Missing name or activity information.'
            }), 400
        
        logger.info(f"Processing request for user: {name}, activity: {activity}")
                
        # Prepare minimal data for the map (no personalization)
        return jsonify({
            'success': True,
            'name': name,
            'activity': activity,
            'location': location_data,
            'social': social_data,
            'redirect_to_map': True,
            'map_url': '/map'
        })
    
    except Exception as e:
        logger.error(f"Error in process_request: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500


@main_bp.route('/geocode', methods=['POST'])
def geocode():
    """Handle both forward and reverse geocoding based on input parameters"""
    try:
        data = request.get_json()
        
        # Check if it's reverse geocoding (latitude/longitude provided)
        if 'latitude' in data and 'longitude' in data:
            return reverse_geocode_coordinates(data)
        
        # Check if it's forward geocoding (city/state provided)
        elif 'city' in data and 'state' in data:
            return forward_geocode_city_state(data)
        
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid request. Provide either (latitude, longitude) or (city, state).'
            }), 400
            
    except Exception as e:
        logger.error(f"Error in geocode endpoint: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing location.'
        }), 500


def reverse_geocode_coordinates(data):
    """Reverse geocode latitude/longitude to get address information"""
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    # Try to convert to float if they're strings
    try:
        if latitude is not None:
            latitude = float(latitude)
        if longitude is not None:
            longitude = float(longitude)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to convert coordinates to float in geocode: {e}")
        return jsonify({
            'success': False,
            'message': 'Invalid coordinate format. Coordinates must be numbers.'
        }), 400
    
    if not validate_coordinates(latitude, longitude):
        return jsonify({
            'success': False,
            'message': 'Invalid latitude or longitude coordinates.'
        }), 400
    
    location_info = geocoding_service.reverse_geocode(latitude, longitude)
    
    if location_info:
        return jsonify({
            'success': True,
            'location': location_info
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to geocode location.'
        }), 500


def forward_geocode_city_state(data):
    """Forward geocode city/state to get coordinates and address information"""
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    
    if not city or not state:
        return jsonify({
            'success': False,
            'message': 'Both city and state are required.'
        }), 400
    
    location_info = geocoding_service.forward_geocode(city, state)
    
    if location_info:
        return jsonify({
            'success': True,
            'location': location_info
        })
    else:
        return jsonify({
            'success': False,
            'message': f'Unable to find location for {city}, {state}. Please check the spelling and try again.'
        }), 404


@main_bp.route('/audio/<audio_id>')
def serve_audio(audio_id: str):
    """Serve generated audio files"""
    try:
        if not tts_service.audio_exists(audio_id):
            abort(404)
        
        audio_path = tts_service.get_audio_path(audio_id)
        return send_file(audio_path, mimetype='audio/mpeg')
        
    except Exception as e:
        logger.error(f"Audio serve error: {e}")
        abort(500)


@main_bp.route('/map/events', methods=['POST'])
def get_map_events():
    """Get events for map display - ranking based solely on user prompt"""
    try:
        data = request.get_json()
        location_data = data.get('location', {})
        personalization_data = data.get('personalization_data', {})
        
        # Extract user activity from the correct location - it's sent directly in the request
        user_activity = data.get('activity', '')
        
        # Also check fallback locations if not found in the main request
        if not user_activity:
            user_activity = personalization_data.get('activity', '')
            if not user_activity:
                # Final fallback: check if it's nested under user_profile
                user_profile = personalization_data.get('user_profile', {})
                user_activity = user_profile.get('activity', '')
        
        logger.info(f"Getting events for activity: '{user_activity}' at location: {location_data}")
        logger.debug(f"Full request data keys: {list(data.keys())}")
        logger.debug(f"Personalization_data: {personalization_data}")
        
        if not user_activity:
            logger.warning(f"No user activity found. Request keys available: {list(data.keys())}")
            logger.warning(f"Personalization_data keys: {list(personalization_data.keys())}")
            if 'user_profile' in personalization_data:
                logger.warning(f"user_profile keys: {list(personalization_data['user_profile'].keys())}")
        
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        
        # Convert coordinates
        try:
            if latitude is not None:
                latitude = float(latitude)
            if longitude is not None:
                longitude = float(longitude)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert coordinates to float: {e}")
            return jsonify({
                'success': False,
                'message': 'Invalid coordinate format. Coordinates must be numbers.'
            }), 400
        
        if not validate_coordinates(latitude, longitude):
            logger.error(f"Got invalid coordinates: {latitude}, {longitude}")
            return jsonify({
                'success': False,
                'message': 'Valid location is required. Please go back to onboarding and share your location to find events near you.'
            }), 400
        
        # Clear previous markers
        mapping_service.clear_markers()
        
        # Get events from unified service with prompt-only ranking
        try:
            unified_events = unified_events_service.search_events(
                location=location_data,
                user_interests=None,  # No user interests - only prompt-based ranking
                user_activity=user_activity,
                personalization_data=None,  # No personalization data
                user_profile=None  # No user profile
            )
            
            if unified_events:
                mapping_service.add_unified_events(unified_events)
                logger.info(f"Added {len(unified_events)} events to map based on prompt: '{user_activity}'")
            else:
                logger.info("No events found")
                
        except Exception as ue_error:
            logger.warning(f"Event search failed: {ue_error}")
        
        # Get map data
        map_data = mapping_service.get_map_data(latitude, longitude)
        category_stats = mapping_service.get_category_stats()
        
        return jsonify({
            'success': True,
            'map_data': map_data,
            'category_stats': category_stats,
            'total_events': len(mapping_service.get_all_markers())
        })
        
    except Exception as e:
        logger.error(f"Error getting map events: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while loading events.'
        }), 500
        
    except Exception as e:
        logger.error(f"Error getting map events: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while loading events.'
        }), 500


@main_bp.route('/map/search', methods=['POST'])
def search_map_events():
    """Search events on the map"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Please provide a search query.'
            }), 400
        
        # Search markers
        matching_markers = mapping_service.search_markers(query)
        
        return jsonify({
            'success': True,
            'markers': [marker.to_dict() for marker in matching_markers],
            'total_results': len(matching_markers)
        })
        
    except Exception as e:
        logger.error(f"Error searching map events: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while searching events.'
        }), 500


@main_bp.route('/map')
def map_view():
    """Render the map page"""
    # The map page will get user data from sessionStorage via JavaScript
    # We provide empty defaults that will be overridden by the frontend
    return render_template('map.html', 
                         name='', 
                         activity='', 
                         location={}, 
                         social={})