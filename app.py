"""
WhatNowAI Flask Application

A multi-step onboarding application that helps users determine their next steps
based on their location, interests, and social media presence.
"""
import logging.config
from flask import Flask

from routes import main_bp
from config.settings import FLASK_CONFIG, LOGGING_CONFIG, AUDIO_DIR, check_api_keys
from services.tts_service import TTSService

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Application factory function
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    
    # Initialize services
    tts_service = TTSService(str(AUDIO_DIR))
    
    # Cleanup old audio files on startup
    try:
        tts_service.cleanup_old_audio()
        logger.info("Audio cleanup completed")
    except Exception as e:
        logger.warning(f"Audio cleanup failed: {e}")
    
    logger.info("WhatNowAI application initialized successfully")
    return app


def main():
    """Main entry point"""
    # Check API keys on startup
    check_api_keys()
    
    app = create_app()
    
    logger.info(f"Starting WhatNowAI on {FLASK_CONFIG['HOST']}:{FLASK_CONFIG['PORT']}")
    app.run(
        debug=FLASK_CONFIG['DEBUG'],
        host=FLASK_CONFIG['HOST'],
        port=FLASK_CONFIG['PORT']
    )


if __name__ == '__main__':
    main()
