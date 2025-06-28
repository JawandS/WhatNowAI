"""
Application configuration
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

def load_secrets():
    """Load API keys and secrets from secrets.txt file"""
    secrets = {}
    secrets_file = BASE_DIR / 'secrets.txt'
    
    if secrets_file.exists():
        try:
            with open(secrets_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        secrets[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not load secrets.txt: {e}")
    
    return secrets

# Load secrets from file
_secrets = load_secrets()

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

# API Keys from secrets.txt file and environment variables (env vars take precedence)
TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY', _secrets.get('TICKETMASTER_CONSUMER_KEY', ''))
ALLEVENTS_API_KEY = os.getenv('ALLEVENTS_API_KEY', _secrets.get('ALLEVENTS_API_KEY', ''))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', _secrets.get('OPENAI_API_KEY', ''))

# Optional API keys for advanced features
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN', _secrets.get('HUGGINGFACE_TOKEN', ''))

# Debug function to check API key status
def check_api_keys():
    """Check which API keys are available"""
    keys_status = {
        'TICKETMASTER_API_KEY': 'SET' if TICKETMASTER_API_KEY else 'NOT SET',
        'ALLEVENTS_API_KEY': 'SET' if ALLEVENTS_API_KEY else 'NOT SET',
        'OPENAI_API_KEY': 'SET' if OPENAI_API_KEY else 'NOT SET',
        'HUGGINGFACE_TOKEN': 'SET' if HUGGINGFACE_TOKEN else 'NOT SET'
    }
    
    print("🔑 API Keys Status:")
    for key, status in keys_status.items():
        print(f"   {key}: {status}")
        if status == 'SET' and key in ['TICKETMASTER_API_KEY', 'ALLEVENTS_API_KEY']:
            print(f"   {key} value: {globals()[key][:10]}...")
    
    return keys_status

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
    'TIMEOUT': 10,
    'MIN_RELEVANCE_SCORE': 0.15  # Minimum relevance score for event filtering
}

# AllEvents API configuration
ALLEVENTS_CONFIG = {
    'BASE_URL': 'https://allevents.developer.azure-api.net/api',
    'SEARCH_RADIUS': 50,  # km
    'MAX_EVENTS': 30,
    'TIMEOUT': 10,
    'MIN_RELEVANCE_SCORE': 0.15  # Minimum relevance score for event filtering
}

# Map configuration
MAP_CONFIG = {
    'DEFAULT_ZOOM': 12,
    'MAX_MARKERS': 50,
    'TILE_SERVER': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'ATTRIBUTION': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}
