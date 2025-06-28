"""
Text-to-Speech service using Edge TTS
"""
import asyncio
import edge_tts
import os
import uuid
from typing import Optional, Tuple
import logging

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


# Pre-defined introduction texts for TTS
INTRODUCTION_TEXTS = {
    "welcome": "Welcome to What Now AI! I'm here to help you figure out your next steps. Let's get started by learning a bit about you.",
    "step_name": "First, please tell me your name and any social media handles you'd like to share. This helps me understand you better.",
    "step_activity": "Great! Now tell me what you want to do or accomplish. Be as specific or general as you'd like.",
    "step_location": "Perfect! Finally, let's get your location so I can provide location-specific recommendations. You can share your location automatically or skip this step.",
    "processing": "Excellent! I'm now analyzing your information and gathering relevant insights. This will just take a moment."
}
