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
from services.user_profiling_service import EnhancedUserProfilingService
from utils.helpers import validate_coordinates, generate_response_text
from config.settings import (AUDIO_DIR, DEFAULT_TTS_VOICE, TICKETMASTER_API_KEY, ALLEVENTS_API_KEY,
                           TICKETMASTER_CONFIG, ALLEVENTS_CONFIG, MAP_CONFIG)

# Import enhanced search
from searchmethods.enhanced_background_search import perform_enhanced_background_search
from searchmethods.background_search import UserProfile

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize services
tts_service = TTSService(str(AUDIO_DIR), DEFAULT_TTS_VOICE)
geocoding_service = GeocodingService()
ticketmaster_service = TicketmasterService(TICKETMASTER_API_KEY, TICKETMASTER_CONFIG)
allevents_service = AllEventsService(ALLEVENTS_API_KEY, ALLEVENTS_CONFIG)
unified_events_service = UnifiedEventsService(ticketmaster_service, allevents_service)
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
    """Handle background processing of user request with enhanced personalization"""
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
        
        # Perform enhanced background search
        logger.info(f"Starting enhanced background search for user: {name}")
        
        # Create user profile for enhanced search
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
        
        # Perform enhanced background search
        enhanced_search_results = None
        search_summaries = None
        personalization_data = None
        
        try:
            enhanced_search_data = perform_enhanced_background_search(user_profile)
            enhanced_search_results = enhanced_search_data.get('raw_results', {})
            search_summaries = enhanced_search_data.get('summaries', {})
            personalization_data = enhanced_search_data.get('enhanced_personalization', {})
            
            logger.info(f"Enhanced background search completed. "
                       f"Personalization score: {enhanced_search_data.get('personalization_score', 0):.1f}%")
            
        except Exception as search_error:
            logger.warning(f"Enhanced background search failed: {search_error}")
            search_summaries = {
                'general': 'Background search temporarily unavailable.',
                'social': 'Social media search temporarily unavailable.',
                'location': 'Location search temporarily unavailable.',
                'activity': 'Activity search temporarily unavailable.'
            }
            personalization_data = {}
        
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
                    'search_results': enhanced_search_results,
                    'search_summaries': search_summaries,
                    'enhanced_personalization': personalization_data
                }
            )
            logger.info(f"Enhanced user profile created with {enhanced_user_profile.profile_completion:.1f}% completion")
            
            # Get recommendation context for events
            recommendation_context = user_profiling_service.get_recommendation_context(enhanced_user_profile)
            
        except Exception as profile_error:
            logger.warning(f"Enhanced user profiling failed: {profile_error}")
            recommendation_context = {}
        
        # Prepare comprehensive personalization data for the map
        comprehensive_personalization_data = {
            'search_results': enhanced_search_results,
            'search_summaries': search_summaries,
            'enhanced_personalization': personalization_data,
            'user_profile': {
                'name': name,
                'activity': activity,
                'location': location_data,
                'social': social_data
            },
            'enhanced_profile': recommendation_context,
            'activity': activity,
            'interests': personalization_data.get('interests', []) if personalization_data else [],
            'behavioral_patterns': personalization_data.get('behavioral_patterns', {}) if personalization_data else {},
            'recommendation_context': personalization_data.get('recommendation_context', {}) if personalization_data else {}
        }
        
        return jsonify({
            'success': True,
            'result': result,
            'name': name,
            'activity': activity,
            'location': location_data,
            'social': social_data,
            'search_summaries': search_summaries,
            'personalization_data': comprehensive_personalization_data,
            'enhanced_profile_completion': enhanced_user_profile.profile_completion if enhanced_user_profile else 0,
            'personalization_score': personalization_data.get('personalization_score', 0) if personalization_data else 0,
            'total_search_results': len(enhanced_search_results) if enhanced_search_results else 0,
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
    """Get events and activities for map display with enhanced personalization"""
    try:
        data = request.get_json()
        location_data = data.get('location', {})
        user_interests = data.get('interests', [])
        user_activity = data.get('activity', '')
        personalization_data = data.get('personalization_data', {})
        
        # Enhanced debug logging
        logger.info(f"=== Enhanced Map Events Request ===")
        logger.info(f"Location data: {location_data}")
        logger.info(f"User interests: {user_interests}")
        logger.info(f"User activity: '{user_activity}'")
        logger.info(f"Personalization data keys: {list(personalization_data.keys()) if personalization_data else 'None'}")
        
        # Extract enhanced personalization data
        enhanced_personalization = personalization_data.get('enhanced_personalization', {})
        recommendation_context = personalization_data.get('recommendation_context', {})
        
        logger.info(f"Enhanced personalization available: {bool(enhanced_personalization)}")
        logger.info(f"Recommendation context available: {bool(recommendation_context)}")
        
        if enhanced_personalization:
            logger.info(f"Enhanced interests count: {len(enhanced_personalization.get('interests', []))}")
            logger.info(f"Behavioral patterns: {list(enhanced_personalization.get('behavioral_patterns', {}).keys())}")
        
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
        
        # Create enhanced user profile for AI analysis
        user_profile_for_ai = None
        
        if enhanced_personalization:
            # Use enhanced personalization data
            user_profile_for_ai = {
                'name': enhanced_personalization.get('user_profile', {}).get('name', ''),
                'location': location_data,
                'primary_activity': user_activity,
                'interests': enhanced_personalization.get('interests', []),
                'behavioral_patterns': enhanced_personalization.get('behavioral_patterns', {}),
                'activity_preferences': enhanced_personalization.get('activity_preferences', {}),
                'social_context': enhanced_personalization.get('social_context', {}),
                'location_insights': enhanced_personalization.get('location_insights', {}),
                'recommendation_context': enhanced_personalization.get('recommendation_context', {}),
                'completion_score': enhanced_personalization.get('personalization_score', 0)
            }
            logger.info(f"Using enhanced personalization profile with {user_profile_for_ai['completion_score']:.1f}% completion")
            
        elif recommendation_context:
            # Fallback to recommendation context
            user_profile_for_ai = recommendation_context
            logger.info(f"Using recommendation context fallback")
            
        elif personalization_data.get('user_profile'):
            # Fallback to basic profile data
            basic_profile = personalization_data['user_profile']
            user_profile_for_ai = {
                'name': basic_profile.get('name', ''),
                'location': basic_profile.get('location', {}),
                'primary_activity': basic_profile.get('activity', user_activity),
                'interests': [],
                'preferences': {'activity_style': 'balanced'},
                'behavioral_patterns': {},
                'activity_context': {'intent': 'seeking'},
                'completion_score': 25
            }
            logger.info(f"Using basic profile fallback for user: {basic_profile.get('name', 'Anonymous')}")
            
        else:
            # Create minimal profile from just the activity
            user_profile_for_ai = {
                'name': 'Anonymous',
                'location': location_data,
                'primary_activity': user_activity,
                'interests': [],
                'preferences': {'activity_style': 'balanced'},
                'behavioral_patterns': {},
                'activity_context': {'intent': 'seeking'},
                'completion_score': 10
            }
            logger.info(f"Created minimal profile from activity: '{user_activity}'")
        
        # Get events from unified service with enhanced personalization
        try:
            unified_events = unified_events_service.search_events(
                location=location_data,
                user_interests=user_interests,
                user_activity=user_activity,
                personalization_data=personalization_data,
                user_profile=user_profile_for_ai
            )
            
            if unified_events:
                mapping_service.add_unified_events(unified_events)
                logger.info(f"Added {len(unified_events)} unified events to map with enhanced personalization")
            else:
                logger.info("No unified events found")
                
        except Exception as ue_error:
            logger.warning(f"Unified search failed: {ue_error}")
        
        # Get map data
        map_data = mapping_service.get_map_data(latitude, longitude)
        category_stats = mapping_service.get_category_stats()
        
        return jsonify({
            'success': True,
            'map_data': map_data,
            'category_stats': category_stats,
            'total_events': len(mapping_service.get_all_markers()),
            'personalization_applied': bool(enhanced_personalization),
            'personalization_score': enhanced_personalization.get('personalization_score', 0) if enhanced_personalization else 0
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