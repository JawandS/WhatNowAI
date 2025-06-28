"""
Flask application routes
"""
from flask import Blueprint, render_template, request, jsonify, abort, send_file
import logging
import time
from typing import Dict, Any

from services.tts_service import TTSService, get_introduction_text, INTRODUCTION_TEXTS
from services.geocoding_service import GeocodingService
from utils.helpers import validate_coordinates, generate_response_text
from config.settings import AUDIO_DIR, DEFAULT_TTS_VOICE
from searchmethods.background_search import UserProfile, perform_background_search

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize services
tts_service = TTSService(str(AUDIO_DIR), DEFAULT_TTS_VOICE)
geocoding_service = GeocodingService()


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
        print(f"search {search_summaries}")
        return jsonify({
            'success': True,
            'result': result,
            'name': name,
            'activity': activity,
            'location': location_data,
            'social': social_data,
            'search_summaries': search_summaries,
            'total_search_results': len(search_results) if search_results else 0
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
