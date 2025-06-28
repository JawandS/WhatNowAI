"""
Text-to-Speech service using Edge TTS
"""
import asyncio
import edge_tts
import os
import uuid
from typing import Optional, Tuple, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-Speech service for generating audio from text"""
    
    def __init__(self, audio_dir: str, voice: str = "en-US-JennyNeural"):
        """
        Initialize TTS service
        
        Args:
            audio_dir: Directory to save audio files
            voice: Voice to use for TTS
        """
        self.audio_dir = audio_dir
        self.voice = voice
        self._ensure_audio_dir()
    
    def _ensure_audio_dir(self) -> None:
        """Ensure audio directory exists"""
        os.makedirs(self.audio_dir, exist_ok=True)
    
    async def generate_audio(self, text: str, voice: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate audio from text using edge-tts
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (optional, uses default if not provided)
            
        Returns:
            Tuple of (audio_id, audio_path) or (None, None) if failed
        """
        try:
            if not text.strip():
                logger.warning("Empty text provided for TTS generation")
                return None, None
            
            # Create unique filename
            audio_id = str(uuid.uuid4())
            audio_path = os.path.join(self.audio_dir, f"{audio_id}.mp3")
            
            # Use provided voice or default
            selected_voice = voice or self.voice
            
            # Generate speech
            communicate = edge_tts.Communicate(text, selected_voice)
            await communicate.save(audio_path)
            
            logger.info(f"Audio generated successfully: {audio_id}")
            return audio_id, audio_path
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None, None
    
    def generate_audio_sync(self, text: str, voice: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous wrapper for TTS generation
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (optional)
            
        Returns:
            Tuple of (audio_id, audio_path) or (None, None) if failed
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.generate_audio(text, voice))
        except Exception as e:
            logger.error(f"TTS Sync Error: {e}")
            return None, None
        finally:
            loop.close()
    
    def get_audio_path(self, audio_id: str) -> str:
        """Get full path for audio file"""
        return os.path.join(self.audio_dir, f"{audio_id}.mp3")
    
    def audio_exists(self, audio_id: str) -> bool:
        """Check if audio file exists"""
        return os.path.exists(self.get_audio_path(audio_id))
    
    def cleanup_old_audio(self, max_age_hours: int = 24) -> None:
        """Clean up old audio files"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.audio_dir):
                if filename.endswith('.mp3'):
                    file_path = os.path.join(self.audio_dir, filename)
                    file_age = current_time - os.path.getctime(file_path)
                    
                    if file_age > max_age_seconds:
                        try:
                            os.remove(file_path)
                            logger.info(f"Cleaned up old audio file: {filename}")
                        except OSError as e:
                            logger.warning(f"Failed to remove old audio file {filename}: {e}")
                            
        except Exception as e:
            logger.error(f"Error during audio cleanup: {e}")


def get_time_based_greeting() -> str:
    """Get time-appropriate greeting"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 22:
        return "Good evening"
    else:
        return "Hello"


def get_introduction_text(step: str, location_data: Optional[Dict] = None) -> str:
    """
    Generate dynamic introduction text based on time, location, and step
    
    Args:
        step: The onboarding step
        location_data: Optional location information
        
    Returns:
        Personalized introduction text
    """
    greeting = get_time_based_greeting()
    
    # Extract location info if available
    location_context = ""
    if location_data:
        city = location_data.get('city', '')
        country = location_data.get('country', '')
        if city and country:
            location_context = f" from {city}, {country}"
        elif country:
            location_context = f" from {country}"
    
    texts = {
        "welcome": f"{greeting}! Welcome to What Now AI. Let's get started!",
        
        "step_name": f"First, I'd love to know your name! You can also share your social media handles.",
        
        "step_activity": f"Perfect! Now tell me, what would you like to do today?",
        
        "step_location": f"Great choice! To give you the best local recommendations, I'll need to know where you are.",
        
        "processing": f"Excellent! Now I'm creating your personalized plan - this will just take a moment."
    }
    
    return texts.get(step, "Let's continue!")


# Backward compatibility - keep static texts as fallback
INTRODUCTION_TEXTS = {
    "welcome": "Good day! Welcome to What Now AI. Let's discover your next adventure!",
    "step_name": "First, what's your name? You can also share social media handles for better recommendations.",
    "step_activity": "Perfect! Now tell me, what would you like to do today?",
    "step_location": "Great! To give you local recommendations, I'll need your location. You can share it or skip this step.",
    "processing": "Excellent! I'm creating your personalized action plan. Just a moment please."
}
