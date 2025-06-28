"""
Flask application routes for WhatNowAI

This module defines all the API endpoints for the WhatNowAI application, including:
- Onboarding flow with TTS integration
- Location services and geocoding
- Event discovery and mapping
- Background research and personalization
"""
from flask import Blueprint, render_template, request, jsonify, abort, send_file
import logging
from typing import Dict, Any

from services.tts_service import TTSService, get_introduction_text, INTRODUCTION_TEXTS
from services.geocoding_service import GeocodingService
from services.ticketmaster_service import TicketmasterService
from services.mapping_service import MappingService
from services.user_profiling_service import EnhancedUserProfilingService
from utils.helpers import validate_coordinates, generate_response_text
from config.settings import (AUDIO_DIR, DEFAULT_TTS_VOICE, TICKETMASTER_API_KEY, 
                           TICKETMASTER_CONFIG, MAP_CONFIG)
from searchmethods.background_search import UserProfile, perform_background_search

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize services
tts_service = TTSService(str(AUDIO_DIR), DEFAULT_TTS_VOICE)
geocoding_service = GeocodingService()
ticketmaster_service = TicketmasterService(TICKETMASTER_API_KEY, TICKETMASTER_CONFIG)
mapping_service = MappingService(MAP_CONFIG)
user_profiling_service = EnhancedUserProfilingService()


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


@main_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Please provide a message.'
            }), 400
        
        # Simple response logic (you can enhance this with AI)
        response = f"I received your message: '{message}'. How can I help you further?"
        
        return jsonify({
            'success': True,
            'response': response
        })
    
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your message.'
        }), 500


@main_bp.route('/process', methods=['POST'])
def process_request():
    """Handle background processing of user request"""
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
        
        # Perform background search
        logger.info(f"Starting background search for user: {name}")
        
        # Create user profile for search
        user_profile = UserProfile(
            name=name,
            location=location_data.get('city', '') + ', ' + location_data.get('country', ''),
            social_handles={
                'twitter': social_data.get('twitter', ''),
                'instagram': social_data.get('instagram', ''),
                'github': social_data.get('github', ''),
                'linkedin': social_data.get('linkedin', ''),
                'tiktok': social_data.get('tiktok', ''),
                'youtube': social_data.get('youtube', '')
            },
            activity=activity
        )
        
        # Perform background search (this may take some time)
        search_results = None
        search_summaries = None
        
        try:
            search_data = perform_background_search(user_profile)
            search_results = search_data.get('raw_results', {})
            search_summaries = search_data.get('summaries', {})
            logger.info(f"Background search completed. Found {search_data.get('total_results', 0)} total results")
        except Exception as search_error:
            logger.warning(f"Background search failed: {search_error}")
            search_summaries = {
                'general': 'Background search temporarily unavailable.',
                'social': 'Social media search temporarily unavailable.',
                'location': 'Location search temporarily unavailable.',
                'activity': 'Activity search temporarily unavailable.'
            }
        
        # Generate response text with search context
        result = generate_response_text(name, activity, location_data, social_data, search_summaries)
        
        # Create enhanced user profile using the new profiling service
        enhanced_user_profile = None
        try:
            enhanced_user_profile = user_profiling_service.create_enhanced_profile(
                name=name,
                location=location_data,
                activity=activity,
                social_data=social_data,
                search_results={
                    'search_results': search_results,
                    'search_summaries': search_summaries
                }
            )
            logger.info(f"Enhanced user profile created with {enhanced_user_profile.profile_completion:.1f}% completion")
            
            # Get recommendation context for events
            recommendation_context = user_profiling_service.get_recommendation_context(enhanced_user_profile)
            
        except Exception as profile_error:
            logger.warning(f"Enhanced user profiling failed: {profile_error}")
            recommendation_context = {}
        
        # Prepare personalization data for later use
        personalization_data = {
            'search_results': search_results,
            'search_summaries': search_summaries,
            'user_profile': {
                'name': name,
                'activity': activity,
                'location': location_data,
                'social': social_data
            },
            'enhanced_profile': recommendation_context,  # Include enhanced profile context
            'activity': activity  # Ensure activity is available at top level
        }
        
        return jsonify({
            'success': True,
            'result': result,
            'name': name,
            'activity': activity,
            'location': location_data,
            'social': social_data,
            'search_summaries': search_summaries,
            'personalization_data': personalization_data,  # Include personalization data
            'enhanced_profile_completion': enhanced_user_profile.profile_completion if enhanced_user_profile else 0,
            'total_search_results': len(search_results) if search_results else 0,
            'redirect_to_map': True,  # Signal frontend to redirect to map
            'map_url': '/map'
        })
    
    except Exception as e:
        logger.error(f"Error in process_request: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500


@main_bp.route('/geocode', methods=['POST'])
def reverse_geocode():
    """Reverse geocode latitude/longitude to get address information"""
    try:
        data = request.get_json()
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
            
    except Exception as e:
        logger.error(f"Error in reverse_geocode: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing location.'
        }), 500


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
    """Get events and activities for map display"""
    try:
        data = request.get_json()
        location_data = data.get('location', {})
        user_interests = data.get('interests', [])
        user_activity = data.get('activity', '')
        personalization_data = data.get('personalization_data', {})  # Enhanced personalization data
        
        # Debug logging for incoming request
        logger.info(f"=== DEBUG: Incoming request data ===")
        logger.info(f"Location data: {location_data}")
        logger.info(f"User interests: {user_interests}")
        logger.info(f"User activity: '{user_activity}'")
        logger.info(f"Personalization data keys: {list(personalization_data.keys()) if personalization_data else 'None'}")
        logger.info(f"Full request data keys: {list(data.keys())}")
        
        # If no personalization data, try to construct basic context from available data
        if not personalization_data:
            logger.warning("No personalization_data in request, attempting to construct basic context")
            
            # Check if user data is available in the request directly
            user_name = data.get('name', '')
            user_social = data.get('social', {})
            
            if user_name or user_activity or user_social:
                logger.info(f"Found basic user data: name='{user_name}', activity='{user_activity}', social={bool(user_social)}")
                
                # Create minimal personalization context
                personalization_data = {
                    'user_profile': {
                        'name': user_name,
                        'activity': user_activity,
                        'location': location_data,
                        'social': user_social
                    },
                    'activity': user_activity,
                    'basic_context': True
                }
                logger.info("Created basic personalization context from request data")
            else:
                logger.warning("No user context data available in request")
        
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        
        # Debug logging
        logger.info(f"Received location_data: {location_data}")
        logger.info(f"Raw coordinates - lat: {latitude} (type: {type(latitude)}), lon: {longitude} (type: {type(longitude)})")
        
        # Try to convert to float if they're strings
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
        
        # Get events from Ticketmaster with enhanced profiling
        logger.info(f"Searching Ticketmaster events for location: {latitude}, {longitude}")
        logger.info(f"Received personalization_data keys: {list(personalization_data.keys()) if personalization_data else 'None'}")
        logger.info(f"User activity from request: '{user_activity}'")
        
        try:
            # Extract enhanced profile data if available
            enhanced_profile_data = personalization_data.get('enhanced_profile', {})
            logger.info(f"Enhanced profile data available: {bool(enhanced_profile_data)}")
            
            # Create a user profile object for the AI analysis
            user_profile_for_ai = None
            if enhanced_profile_data:
                user_profile_for_ai = enhanced_profile_data
                logger.info(f"Using enhanced profile with {len(enhanced_profile_data.get('interests', []))} interests")
            elif personalization_data.get('user_profile'):
                # Fallback to basic profile data
                basic_profile = personalization_data['user_profile']
                user_profile_for_ai = {
                    'name': basic_profile.get('name', ''),
                    'location': basic_profile.get('location', {}),
                    'primary_activity': basic_profile.get('activity', user_activity),  # Use current activity if not in profile
                    'interests': [],
                    'preferences': {'activity_style': 'balanced'},
                    'behavioral_patterns': {},
                    'activity_context': {'intent': 'seeking'},
                    'completion_score': 25  # Basic completion
                }
                logger.info(f"Using basic profile fallback for user: {basic_profile.get('name', 'Anonymous')}")
            elif user_activity:
                # Create minimal profile from just the activity
                user_profile_for_ai = {
                    'name': 'Anonymous',
                    'location': location_data,
                    'primary_activity': user_activity,
                    'interests': [],
                    'preferences': {'activity_style': 'balanced'},
                    'behavioral_patterns': {},
                    'activity_context': {'intent': 'seeking'},
                    'completion_score': 10  # Minimal completion
                }
                logger.info(f"Created minimal profile from activity: '{user_activity}'")
            else:
                logger.warning("No personalization data available - will use basic search only")
            
            ticketmaster_events = ticketmaster_service.search_events(
                location=location_data,
                user_interests=user_interests,
                user_activity=user_activity,
                personalization_data=personalization_data,
                user_profile=user_profile_for_ai  # Pass enhanced profile to AI ranking
            )
            
            if ticketmaster_events:
                mapping_service.add_ticketmaster_events(ticketmaster_events)
                logger.info(f"Added {len(ticketmaster_events)} Ticketmaster events to map")
            else:
                logger.info("No Ticketmaster events found")
                
        except Exception as tm_error:
            logger.warning(f"Ticketmaster search failed: {tm_error}")
        
        # TODO: Add other API integrations here
        # mapping_service.add_eventbrite_events(eventbrite_events)
        # mapping_service.add_meetup_events(meetup_events)
        
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
