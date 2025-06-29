"""
Unified Events Service

This service coordinates multiple event APIs (Ticketmaster, AllEvents, etc.),
applies AI-powered filtering and ranking, and provides a unified interface
for event discovery with advanced personalization.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class EventSource:
    """Metadata about an event source"""
    name: str
    priority: float  # Higher priority = more trusted source
    reliability: float  # 0-1 reliability score
    coverage: str  # geographical coverage description


class UnifiedEventsService:
    """
    Unified service that coordinates multiple event sources and applies AI evaluation
    """
    
    def __init__(self, ticketmaster_service=None, allevents_service=None, ai_service=None):
        """
        Initialize the unified events service
        
        Args:
            ticketmaster_service: Ticketmaster API service instance
            allevents_service: AllEvents API service instance  
            ai_service: AI service for intelligent filtering (optional)
        """
        self.ticketmaster_service = ticketmaster_service
        self.allevents_service = allevents_service
        self.ai_service = ai_service
        
        # Define event sources with metadata
        self.event_sources = {
            'ticketmaster': EventSource(
                name='Ticketmaster',
                priority=0.9,
                reliability=0.95,
                coverage='Global, strong in North America and Europe'
            ),
            'allevents': EventSource(
                name='AllEvents',
                priority=0.7,
                reliability=0.8,
                coverage='Global, diverse event types'
            )
        }
        
        # Configuration
        self.max_events_per_source = 50
        self.final_event_limit = 30
        self.ai_confidence_threshold = 0.6
        
    def search_events(self, location: Dict[str, Any], user_interests: List[str] = None,
                            user_activity: str = "", personalization_data: Dict[str, Any] = None,
                            user_profile: Any = None) -> List[Any]:
        """
        Search for events from all available sources, group them, and apply AI evaluation
        
        Args:
            location: Dictionary with latitude, longitude, city, country
            user_interests: List of user interest categories
            user_activity: What the user wants to do
            personalization_data: Enhanced personalization data from background search
            user_profile: Enhanced user profile from user_profiling_service
            
        Returns:
            List of AI-evaluated and ranked events
        """
        logger.info(f"Starting unified event search for location: {location}")
        logger.info(f"User activity: '{user_activity}', interests: {user_interests}")
        
        all_events = []
        sources_used = []
        search_results = {}
        
        # Collect events from all available sources in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_source = {}
            
            # Submit search tasks for each available service
            if self.ticketmaster_service:
                future = executor.submit(
                    self._search_source_safely,
                    'ticketmaster',
                    self.ticketmaster_service,
                    location, user_interests, user_activity, personalization_data, user_profile
                )
                future_to_source[future] = 'ticketmaster'
            
            if self.allevents_service:
                future = executor.submit(
                    self._search_source_safely,
                    'allevents',
                    self.allevents_service,
                    location, user_interests, user_activity, personalization_data, user_profile
                )
                future_to_source[future] = 'allevents'
            
            # Collect results as they complete
            for future in as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    events = future.result(timeout=30)  # 30 second timeout per source
                    if events:
                        all_events.extend(events)
                        sources_used.append(source_name)
                        search_results[source_name] = len(events)
                        logger.info(f"✅ {source_name}: Found {len(events)} events")
                    else:
                        logger.info(f"⚠️ {source_name}: No events found")
                        search_results[source_name] = 0
                except Exception as e:
                    logger.error(f"❌ {source_name}: Search failed - {e}")
                    search_results[source_name] = 0
        
        logger.info(f"Total events collected from all sources: {len(all_events)}")
        
        # Remove duplicates and group similar events
        deduplicated_events = self._deduplicate_events(all_events)
        logger.info(f"Events after deduplication: {len(deduplicated_events)}")
        
        # Apply AI-powered evaluation and ranking
        ai_results = self._apply_ai_evaluation(
            deduplicated_events, user_profile, user_activity, personalization_data
        )
        
        # Final filtering and ranking
        final_events = self._final_ranking_and_filtering(
            ai_results.get('ranked_events', deduplicated_events),
            user_profile,
            user_activity
        )
        
        # Remove cost information as requested
        final_events = self._remove_cost_information(final_events)
        
        logger.info(f"Final events returned after AI evaluation: {len(final_events)}")
        
        return final_events
    
    def _search_source_safely(self, source_name: str, service: Any, *args) -> List[Any]:
        """Safely search a single event source with error handling"""
        try:
            logger.info(f"🔍 Searching {source_name}...")
            events = service.search_events(*args)
            return events if events else []
        except Exception as e:
            logger.error(f"Error searching {source_name}: {e}")
            return []
    
    def _deduplicate_events(self, events: List[Any]) -> List[Any]:
        """
        Remove duplicate events and group similar ones
        Uses event name, venue, and date for deduplication
        """
        seen_events = {}
        deduplicated = []
        
        for event in events:
            # Create a unique key for the event
            event_key = self._create_event_key(event)
            
            if event_key not in seen_events:
                seen_events[event_key] = event
                deduplicated.append(event)
            else:
                # If we find a duplicate, keep the one with higher reliability
                existing_event = seen_events[event_key]
                if self._should_replace_event(existing_event, event):
                    # Replace the existing event
                    deduplicated.remove(existing_event)
                    deduplicated.append(event)
                    seen_events[event_key] = event
        
        return deduplicated
    
    def _create_event_key(self, event: Any) -> str:
        """Create a unique key for event deduplication"""
        try:
            name = getattr(event, 'name', '').lower().strip()
            venue = getattr(event, 'venue', '').lower().strip()
            date = getattr(event, 'date', '').strip()
            
            # Normalize the name (remove common variations)
            name = self._normalize_event_name(name)
            
            return f"{name}|{venue}|{date}"
        except Exception as e:
            logger.warning(f"Error creating event key: {e}")
            return f"unknown_{id(event)}"
    
    def _normalize_event_name(self, name: str) -> str:
        """Normalize event name for better deduplication"""
        import re
        
        # Remove common prefixes/suffixes and normalize
        name = re.sub(r'\b(the|a|an)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _should_replace_event(self, existing: Any, new: Any) -> bool:
        """Determine if a new event should replace an existing duplicate"""
        try:
            # Prefer events with more information
            existing_score = self._calculate_completeness_score(existing)
            new_score = self._calculate_completeness_score(new)
            
            return new_score > existing_score
        except Exception:
            return False
    
    def _calculate_completeness_score(self, event: Any) -> float:
        """Calculate how complete an event's information is"""
        score = 0.0
        
        # Check various fields for completeness
        if getattr(event, 'name', ''):
            score += 1.0
        if getattr(event, 'description', ''):
            score += 1.0
        if getattr(event, 'image_url', ''):
            score += 0.5
        if getattr(event, 'venue', '') != 'TBA':
            score += 0.5
        if getattr(event, 'address', ''):
            score += 0.5
        if getattr(event, 'time', '') != 'TBA':
            score += 0.5
        if getattr(event, 'url', ''):
            score += 0.5
        
        # Prefer events from higher reliability sources
        event_id = getattr(event, 'id', '')
        if 'ticketmaster' in event_id or hasattr(event, 'source') and 'ticketmaster' in str(getattr(event, 'source', '')):
            score += 0.5  # Ticketmaster bonus
        
        return score
    
    def _apply_ai_evaluation(self, events: List[Any], user_profile: Any, 
                           user_activity: str, personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI-powered evaluation and ranking to events"""
        try:
            # If we have an AI service, use it for advanced evaluation
            if self.ai_service:
                return self._advanced_ai_evaluation(events, user_profile, user_activity, personalization_data)
            else:
                # Fallback to rule-based evaluation
                return self._rule_based_evaluation(events, user_profile, user_activity, personalization_data)
        except Exception as e:
            logger.error(f"AI evaluation failed, using fallback: {e}")
            return {
                'ranked_events': events,
                'insights': {'error': str(e), 'method': 'fallback'}
            }
    
    def _rule_based_evaluation(self, events: List[Any], user_profile: Any,
                             user_activity: str, personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based evaluation and ranking when AI service is not available"""
        
        logger.info("Applying rule-based event evaluation")
        
        for event in events:
            score = 0.5  # Base score
            factors = {}
            
            # Activity matching
            if user_activity:
                activity_score = self._calculate_activity_match(event, user_activity)
                score += activity_score * 0.3
                factors['activity_match'] = activity_score
            
            # Interest matching
            if user_profile:
                interest_score = self._calculate_interest_match(event, user_profile, personalization_data)
                score += interest_score * 0.3
                factors['interest_match'] = interest_score
            
            # Time relevance (prefer closer dates)
            time_score = self._calculate_time_relevance(event)
            score += time_score * 0.2
            factors['time_relevance'] = time_score
            
            # Completeness bonus
            completeness_score = self._calculate_completeness_score(event) / 5.0
            score += completeness_score * 0.2
            factors['completeness'] = completeness_score
            
            # Set the relevance score
            event.relevance_score = min(score, 1.0)
            event.personalization_factors = factors
            event.recommendation_reason = self._generate_recommendation_reason(factors, user_activity)
        
        # Sort by relevance score
        ranked_events = sorted(events, key=lambda x: getattr(x, 'relevance_score', 0), reverse=True)
        
        insights = {
            'method': 'rule_based',
            'total_evaluated': len(events),
            'avg_score': sum(getattr(e, 'relevance_score', 0) for e in events) / len(events) if events else 0,
            'top_factors': ['activity_match', 'interest_match', 'time_relevance', 'completeness']
        }
        
        return {
            'ranked_events': ranked_events,
            'insights': insights
        }
    
    def _calculate_activity_match(self, event: Any, user_activity: str) -> float:
        """Calculate how well an event matches the user's stated activity"""
        try:
            event_text = f"{getattr(event, 'name', '')} {getattr(event, 'description', '')} {getattr(event, 'category', '')}".lower()
            activity_lower = user_activity.lower()
            
            # Simple keyword matching
            activity_words = [word for word in activity_lower.split() if len(word) > 2]
            matches = sum(1 for word in activity_words if word in event_text)
            
            if not activity_words:
                return 0.0
            
            return min(matches / len(activity_words), 1.0)
        except Exception:
            return 0.0
    
    def _calculate_interest_match(self, event: Any, user_profile: Any, personalization_data: Dict[str, Any]) -> float:
        """Calculate how well an event matches the user's interests"""
        try:
            score = 0.0
            
            # Check enhanced personalization data first
            if personalization_data and personalization_data.get('enhanced_personalization'):
                enhanced_data = personalization_data['enhanced_personalization']
                interests = enhanced_data.get('interests', [])
                
                event_category = getattr(event, 'category', '').lower()
                event_name = getattr(event, 'name', '').lower()
                event_description = getattr(event, 'description', '').lower()
                event_text = f"{event_name} {event_description}"
                
                for interest in interests:
                    interest_category = interest.get('category', '').lower()
                    interest_keywords = interest.get('keywords', [])
                    confidence = interest.get('confidence', 0)
                    
                    # Category match
                    if interest_category == event_category or interest_category in event_category:
                        score += confidence * 0.5
                    
                    # Keyword matches
                    keyword_matches = sum(1 for keyword in interest_keywords if keyword.lower() in event_text)
                    if keyword_matches > 0 and interest_keywords:
                        score += (keyword_matches / len(interest_keywords)) * confidence * 0.3
            
            # Fallback to basic user profile
            elif user_profile and hasattr(user_profile, 'get'):
                interests = user_profile.get('interests', [])
                event_category = getattr(event, 'category', '').lower()
                
                for interest in interests:
                    if isinstance(interest, dict):
                        interest_category = interest.get('category', '').lower()
                    elif hasattr(interest, 'category'):
                        interest_category = interest.category.lower()
                    else:
                        interest_category = str(interest).lower()
                    
                    if interest_category == event_category or interest_category in event_category:
                        score += 0.4
            
            return min(score, 1.0)
        except Exception as e:
            logger.debug(f"Error calculating interest match: {e}")
            return 0.0
    
    def _calculate_time_relevance(self, event: Any) -> float:
        """Calculate time relevance (prefer events happening soon)"""
        try:
            from datetime import datetime, timedelta
            
            event_date = getattr(event, 'date', '')
            if not event_date or event_date == 'TBA':
                return 0.3  # Neutral score for unknown dates
            
            # Try to parse the date
            try:
                # Assuming date format is YYYY-MM-DD or similar
                event_dt = datetime.strptime(event_date[:10], '%Y-%m-%d')
                now = datetime.now()
                days_diff = (event_dt - now).days
                
                if days_diff < 0:
                    return 0.1  # Past event
                elif days_diff <= 7:
                    return 1.0  # This week
                elif days_diff <= 14:
                    return 0.8  # Next week
                elif days_diff <= 30:
                    return 0.6  # This month
                else:
                    return 0.4  # Future
            except ValueError:
                return 0.3  # Can't parse date
                
        except Exception:
            return 0.3
    
    def _generate_recommendation_reason(self, factors: Dict[str, float], user_activity: str) -> str:
        """Generate a human-readable recommendation reason"""
        reasons = []
        
        if factors.get('activity_match', 0) > 0.7:
            reasons.append(f"closely matches your interest in '{user_activity}'")
        elif factors.get('activity_match', 0) > 0.4:
            reasons.append(f"relates to your interest in '{user_activity}'")
        
        if factors.get('interest_match', 0) > 0.7:
            reasons.append("aligns with your profile interests")
        elif factors.get('interest_match', 0) > 0.4:
            reasons.append("matches some of your interests")
        
        if factors.get('time_relevance', 0) > 0.8:
            reasons.append("happening soon")
        
        if factors.get('completeness', 0) > 0.8:
            reasons.append("has detailed information available")
        
        if not reasons:
            return "recommended based on your location and general interests"
        
        return "Recommended because it " + " and ".join(reasons)
    
    def _final_ranking_and_filtering(self, events: List[Any], user_profile: Any, user_activity: str) -> List[Any]:
        """Apply final ranking and filtering to events"""
        # Filter out events with very low relevance scores
        filtered_events = [e for e in events if getattr(e, 'relevance_score', 0) > 0.2]
        
        # Limit to configured maximum
        final_events = filtered_events[:self.final_event_limit]
        
        logger.info(f"Final filtering: {len(events)} -> {len(filtered_events)} -> {len(final_events)}")
        
        return final_events
    
    def _remove_cost_information(self, events: List[Any]) -> List[Any]:
        """Remove cost/price information from events as requested"""
        for event in events:
            # Set price fields to None
            if hasattr(event, 'price_min'):
                event.price_min = None
            if hasattr(event, 'price_max'):
                event.price_max = None
        
        return events
    
    def _advanced_ai_evaluation(self, events: List[Any], user_profile: Any,
                              user_activity: str, personalization_data: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced AI evaluation using external AI service (placeholder for future implementation)"""
        # This would integrate with OpenAI or other AI services for more sophisticated evaluation
        # For now, fall back to rule-based evaluation
        logger.info("Advanced AI evaluation not yet implemented, using rule-based evaluation")
        return self._rule_based_evaluation(events, user_profile, user_activity, personalization_data)