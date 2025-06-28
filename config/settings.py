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
