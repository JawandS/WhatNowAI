"""
Application configuration
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Audio configuration
AUDIO_DIR = BASE_DIR / 'static' / 'audio'
DEFAULT_TTS_VOICE = "en-US-JennyNeural"
AUDIO_CLEANUP_HOURS = 24

# Flask configuration
FLASK_CONFIG = {
    'DEBUG': True,
    'HOST': '0.0.0.0',
    'PORT': 5002
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}

# Geocoding configuration
GEOCODING_CONFIG = {
    'USER_AGENT': 'WhatNowAI/1.0',
    'TIMEOUT': 10
}

# API Keys from environment variables
ASSEMBLY_AI_KEY = os.getenv('ASSEMBLY_AI_KEY', '')
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN', '')
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Search configuration
SEARCH_CONFIG = {
    'MAX_RESULTS_PER_SOURCE': 3,  # Reduced for faster searches
    'TIMEOUT': 5,  # Reduced timeout per request
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'SOCIAL_PLATFORMS': ['twitter', 'linkedin', 'instagram', 'github', 'tiktok', 'youtube'],
    'MAX_CONCURRENT_REQUESTS': 3,  # Reduced for faster processing
    'FOCUS_ON_USER': True,  # Only search for the specific user, not celebrities/general info
    'LOCAL_ACTIVITY_SEARCH': True,  # Include local activity searches
    'SEARCH_TIMEOUT': 10,  # Total search timeout in seconds
    'SKIP_GENERAL_SEARCH': True  # Skip general name searches
}

# Ticketmaster API configuration
TICKETMASTER_CONFIG = {
    'BASE_URL': 'https://app.ticketmaster.com/discovery/v2',
    'SEARCH_RADIUS': 50,  # miles
    'MAX_EVENTS': 20,
    'DEFAULT_CATEGORIES': ['music', 'sports', 'arts', 'miscellaneous'],
    'TIMEOUT': 10
}

# Map configuration
MAP_CONFIG = {
    'DEFAULT_ZOOM': 12,
    'MAX_MARKERS': 50,
    'TILE_SERVER': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'ATTRIBUTION': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}
