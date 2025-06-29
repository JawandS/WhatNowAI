"""
OpenAI Service for intelligent event ranking

This service uses OpenAI's GPT-4o-mini to rank events based on user activity and preferences.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for using OpenAI to intelligently rank and filter events"""
    
    def __init__(self, api_key: str = None):
        """Initialize OpenAI service
        
        Args:
            api_key: OpenAI API key. If None, will use OPENAI_API_KEY from settings
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            logger.warning("OpenAI API key not found. Event ranking will fall back to basic text matching.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI service initialized successfully")
    
    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return self.client is not None
    
    def rank_events_by_activity(self, events: List[Any], user_activity: str, max_events: int = 20) -> List[Dict[str, Any]]:
        """
        Use OpenAI to rank events based on user activity description
        
        Args:
            events: List of event objects to rank
            user_activity: User's description of what they want to do
            max_events: Maximum number of events to return
            
        Returns:
            List of dictionaries with event info and ranking
        """
        if not self.is_available():
            logger.warning("OpenAI not available, falling back to basic ranking")
            return self._fallback_ranking(events, user_activity, max_events)
        
        if not events:
            return []
        
        if not user_activity.strip():
            logger.info("No user activity provided, returning events with neutral scores")
            return self._neutral_ranking(events, max_events)
        
        try:
            # Prepare event data for OpenAI
            event_data = []
            for i, event in enumerate(events[:50]):  # Limit to first 50 events for API efficiency
                event_info = {
                    'id': i,
                    'name': getattr(event, 'name', 'Unknown Event'),
                    'description': getattr(event, 'description', ''),
                    'category': getattr(event, 'category', ''),
                    'venue': getattr(event, 'venue', ''),
                    'date': getattr(event, 'date', ''),
                    'time': getattr(event, 'time', '')
                }
                event_data.append(event_info)
            
            # Create the prompt
            prompt = self._create_ranking_prompt(user_activity, event_data)
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert event recommendation system. Your job is to rank events based on how well they match what the user wants to do. Be objective and helpful."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse the response
            rankings = self._parse_ranking_response(response.choices[0].message.content, events, event_data)
            
            logger.info(f"OpenAI ranked {len(rankings)} events for activity: '{user_activity}'")
            return rankings[:max_events]
            
        except Exception as e:
            logger.error(f"Error calling OpenAI for event ranking: {e}")
            return self._fallback_ranking(events, user_activity, max_events)
    
    def _create_ranking_prompt(self, user_activity: str, event_data: List[Dict]) -> str:
        """Create a prompt for OpenAI to rank events"""
        events_json = json.dumps(event_data, indent=2)
        
        prompt = f"""
I want to do: "{user_activity}"

Please rank these events from most relevant (1) to least relevant based on how well they match what I want to do. Consider:
- Direct activity matches (if I want "comedy", prioritize comedy shows)
- Related activities (if I want "fun night out", consider concerts, shows, bars)
- Event type and description relevance
- Practical considerations (timing, venue type)

Events to rank:
{events_json}

Return your response as a JSON array with this exact format:
[
  {{
    "event_id": 0,
    "relevance_score": 0.95,
    "reason": "Perfect match - this is exactly what you're looking for"
  }},
  {{
    "event_id": 1,
    "relevance_score": 0.75,
    "reason": "Good option - similar activity type"
  }}
]

Score from 0.0 (not relevant) to 1.0 (perfect match). Include a brief reason for each ranking.
Rank ALL events provided, not just the top ones.
"""
        return prompt
    
    def _parse_ranking_response(self, response_text: str, original_events: List[Any], event_data: List[Dict]) -> List[Dict[str, Any]]:
        """Parse OpenAI response and return ranked events"""
        try:
            # Try to extract JSON from the response
            response_text = response_text.strip()
            
            # Handle cases where response might have extra text around JSON
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                rankings = json.loads(json_text)
            else:
                raise ValueError("No JSON array found in response")
            
            # Map rankings back to original events
            ranked_events = []
            for ranking in rankings:
                event_id = ranking.get('event_id', 0)
                if 0 <= event_id < len(original_events):
                    event = original_events[event_id]
                    event.relevance_score = ranking.get('relevance_score', 0.5)
                    event.recommendation_reason = ranking.get('reason', 'AI recommendation')
                    ranked_events.append(event)
            
            # Sort by relevance score
            ranked_events.sort(key=lambda x: getattr(x, 'relevance_score', 0), reverse=True)
            
            return ranked_events
            
        except Exception as e:
            logger.error(f"Error parsing OpenAI ranking response: {e}")
            logger.debug(f"Response text: {response_text}")
            return self._fallback_ranking(original_events, "", len(original_events))
    
    def _fallback_ranking(self, events: List[Any], user_activity: str, max_events: int) -> List[Any]:
        """Fallback ranking using basic text matching when OpenAI is not available"""
        if not user_activity.strip():
            return self._neutral_ranking(events, max_events)
        
        activity_words = user_activity.lower().split()
        
        for event in events:
            event_text = f"{getattr(event, 'name', '')} {getattr(event, 'description', '')} {getattr(event, 'category', '')}".lower()
            
            # Count word matches
            matches = sum(1 for word in activity_words if word in event_text)
            score = min(matches / len(activity_words), 1.0) if activity_words else 0.5
            
            event.relevance_score = score
            event.recommendation_reason = f"Text matching score: {score:.2f}"
        
        # Sort by relevance score
        events.sort(key=lambda x: getattr(x, 'relevance_score', 0), reverse=True)
        
        return events[:max_events]
    
    def _neutral_ranking(self, events: List[Any], max_events: int) -> List[Any]:
        """Return events with neutral ranking when no activity is provided"""
        for event in events:
            event.relevance_score = 0.5
            event.recommendation_reason = "Found near your location"
        
        return events[:max_events]
