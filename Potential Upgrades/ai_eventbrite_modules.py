# searchmethods/ai/ai_processor.py
"""
AI-powered data processing and interest extraction
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import openai
import torch
from transformers import pipeline, AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from ..core import SearchResult, UserInterest, EnhancedUserProfile

logger = logging.getLogger(__name__)


@dataclass
class AIConfig:
    """AI configuration"""
    use_openai: bool = False
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    use_huggingface: bool = True
    hf_model: str = "facebook/bart-large-mnli"
    use_local_embeddings: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    
    def __post_init__(self):
        if self.use_openai and not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            if not self.openai_api_key:
                logger.warning("OpenAI API key not found, disabling OpenAI features")
                self.use_openai = False


class AIProcessor:
    """AI-powered data processor"""
    
    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig()
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models"""
        self.models = {}
        
        # Initialize OpenAI
        if self.config.use_openai and self.config.openai_api_key:
            openai.api_key = self.config.openai_api_key
            self.models['openai'] = True
            logger.info("OpenAI initialized")
        
        # Initialize HuggingFace models
        if self.config.use_huggingface:
            try:
                # Zero-shot classification
                self.models['classifier'] = pipeline(
                    "zero-shot-classification",
                    model=self.config.hf_model
                )
                
                # Named Entity Recognition
                self.models['ner'] = pipeline(
                    "ner",
                    model="dslim/bert-base-NER",
                    aggregation_strategy="simple"
                )
                
                # Sentiment Analysis
                self.models['sentiment'] = pipeline(
                    "sentiment-analysis",
                    model="nlptown/bert-base-multilingual-uncased-sentiment"
                )
                
                logger.info("HuggingFace models initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize HuggingFace models: {e}")
                self.config.use_huggingface = False
        
        # Initialize embedding model
        if self.config.use_local_embeddings:
            try:
                self.models['embeddings'] = SentenceTransformer(
                    self.config.embedding_model
                )
                logger.info("Embedding model initialized")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                self.config.use_local_embeddings = False
    
    async def extract_interests_with_ai(
        self, 
        search_results: List[SearchResult],
        user_profile: EnhancedUserProfile
    ) -> List[UserInterest]:
        """Extract interests using AI"""
        interests = []
        
        # Method 1: OpenAI extraction
        if self.config.use_openai:
            openai_interests = await self._extract_with_openai(search_results, user_profile)
            interests.extend(openai_interests)
        
        # Method 2: HuggingFace zero-shot classification
        if self.config.use_huggingface:
            hf_interests = self._extract_with_huggingface(search_results)
            interests.extend(hf_interests)
        
        # Method 3: Embedding-based clustering
        if self.config.use_local_embeddings:
            embedding_interests = self._extract_with_embeddings(search_results)
            interests.extend(embedding_interests)
        
        # Deduplicate and merge interests
        return self._merge_interests(interests)
    
    async def _extract_with_openai(
        self, 
        results: List[SearchResult],
        user_profile: EnhancedUserProfile
    ) -> List[UserInterest]:
        """Extract interests using OpenAI"""
        interests = []
        
        # Prepare context
        context = self._prepare_context(results, user_profile)
        
        try:
            prompt = f"""
            Based on the following information about {user_profile.full_name}, 
            extract their interests and hobbies. For each interest found, 
            provide a category, relevant keywords, and confidence score (0-1).
            
            Context:
            {context}
            
            Return the response as a JSON array with objects containing:
            - category: string (e.g., "music", "sports", "technology")
            - keywords: array of strings
            - confidence: float (0-1)
            - evidence: string (brief explanation)
            
            Focus on genuine interests, not just mentions. If someone owned a dog,
            you might infer they like animals. If they attend concerts, they like music.
            """
            
            response = await openai.ChatCompletion.acreate(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing text to extract people's interests and hobbies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            import json
            try:
                interest_data = json.loads(response.choices[0].message.content)
                
                for item in interest_data:
                    interest = UserInterest(
                        category=item['category'],
                        keywords=item['keywords'],
                        confidence=float(item['confidence']),
                        source='openai',
                        evidence=item['evidence']
                    )
                    interests.append(interest)
                    
            except json.JSONDecodeError:
                logger.error("Failed to parse OpenAI response as JSON")
                
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
        
        return interests
    
    def _extract_with_huggingface(self, results: List[SearchResult]) -> List[UserInterest]:
        """Extract interests using HuggingFace models"""
        interests = []
        
        if 'classifier' not in self.models:
            return interests
        
        # Define interest categories
        candidate_labels = [
            "music", "sports", "technology", "art", "food", "travel",
            "fitness", "gaming", "education", "business", "entertainment",
            "fashion", "nature", "social causes", "photography", "writing",
            "science", "politics", "health", "spirituality", "crafts"
        ]
        
        # Process each result
        for result in results[:10]:  # Limit for performance
            try:
                # Classify content
                classification = self.models['classifier'](
                    result.content[:500],  # Limit text length
                    candidate_labels=candidate_labels,
                    multi_label=True
                )
                
                # Extract high-confidence interests
                for label, score in zip(classification['labels'], classification['scores']):
                    if score > 0.5:  # Confidence threshold
                        # Extract keywords using NER
                        entities = self.models['ner'](result.content[:500])
                        keywords = [e['word'] for e in entities if e['entity_group'] in ['PER', 'ORG', 'LOC']]
                        
                        interest = UserInterest(
                            category=label,
                            keywords=keywords[:5],  # Top 5 keywords
                            confidence=score,
                            source='huggingface_classifier',
                            evidence=f"Found in: {result.title[:50]}..."
                        )
                        interests.append(interest)
                        
            except Exception as e:
                logger.debug(f"HuggingFace processing error: {e}")
                continue
        
        return interests
    
    def _extract_with_embeddings(self, results: List[SearchResult]) -> List[UserInterest]:
        """Extract interests using embedding clustering"""
        interests = []
        
        if 'embeddings' not in self.models or len(results) < 5:
            return interests
        
        try:
            # Get embeddings for all results
            texts = [f"{r.title} {r.content[:300]}" for r in results]
            embeddings = self.models['embeddings'].encode(texts)
            
            # Cluster embeddings
            n_clusters = min(5, len(results) // 3)
            if n_clusters > 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                clusters = kmeans.fit_predict(embeddings)
                
                # Analyze each cluster
                for cluster_id in range(n_clusters):
                    cluster_indices = np.where(clusters == cluster_id)[0]
                    cluster_texts = [texts[i] for i in cluster_indices]
                    
                    # Find common themes in cluster
                    category, keywords = self._analyze_cluster(cluster_texts)
                    
                    if category:
                        interest = UserInterest(
                            category=category,
                            keywords=keywords,
                            confidence=0.6,  # Medium confidence for clustering
                            source='embedding_clustering',
                            evidence=f"Found in cluster of {len(cluster_indices)} related results"
                        )
                        interests.append(interest)
                        
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
        
        return interests
    
    def _analyze_cluster(self, texts: List[str]) -> tuple:
        """Analyze a cluster of texts to find common theme"""
        # Simple keyword extraction
        from collections import Counter
        import re
        
        # Extract words from all texts
        all_words = []
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            all_words.extend(words)
        
        # Count word frequencies
        word_freq = Counter(all_words)
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                       'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 
                       'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 
                       'does', 'did', 'will', 'would', 'could', 'should', 'may', 
                       'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        for word in common_words:
            word_freq.pop(word, None)
        
        # Get top keywords
        top_keywords = [word for word, _ in word_freq.most_common(10)]
        
        # Map keywords to categories
        category_keywords = {
            'technology': ['tech', 'software', 'code', 'programming', 'computer', 'app', 'developer'],
            'music': ['music', 'concert', 'band', 'song', 'album', 'artist', 'spotify'],
            'sports': ['sports', 'game', 'team', 'player', 'fitness', 'gym', 'athletic'],
            'food': ['food', 'restaurant', 'cooking', 'recipe', 'chef', 'cuisine', 'dining'],
            'travel': ['travel', 'trip', 'vacation', 'hotel', 'flight', 'destination', 'tourism'],
            'business': ['business', 'company', 'startup', 'entrepreneur', 'marketing', 'finance'],
            'education': ['education', 'learning', 'course', 'university', 'student', 'teacher']
        }
        
        # Find best matching category
        best_category = None
        best_score = 0
        
        for category, cat_keywords in category_keywords.items():
            score = sum(1 for kw in cat_keywords if any(kw in word for word in top_keywords))
            if score > best_score:
                best_score = score
                best_category = category
        
        return best_category, top_keywords[:5]
    
    def _prepare_context(self, results: List[SearchResult], user_profile: EnhancedUserProfile) -> str:
        """Prepare context for AI analysis"""
        context_parts = []
        
        # Add user info
        context_parts.append(f"Name: {user_profile.full_name}")
        context_parts.append(f"Location: {user_profile.location.get('city', 'Unknown')}")
        context_parts.append(f"Stated interest: {user_profile.activity}")
        
        # Add search results
        context_parts.append("\nSearch Results:")
        for i, result in enumerate(results[:10]):  # Limit to 10 results
            context_parts.append(f"\n{i+1}. {result.title}")
            context_parts.append(f"   {result.content[:200]}...")
        
        return '\n'.join(context_parts)
    
    def _merge_interests(self, interests: List[UserInterest]) -> List[UserInterest]:
        """Merge and deduplicate interests from different sources"""
        merged = {}
        
        for interest in interests:
            key = interest.category
            
            if key not in merged:
                merged[key] = interest
            else:
                # Merge keywords
                existing = merged[key]
                all_keywords = list(set(existing.keywords + interest.keywords))
                
                # Use highest confidence
                if interest.confidence > existing.confidence:
                    existing.confidence = interest.confidence
                    existing.evidence = interest.evidence
                
                existing.keywords = all_keywords[:10]  # Limit keywords
        
        return list(merged.values())
    
    async def enhance_profile_with_ai(
        self,
        user_profile: EnhancedUserProfile,
        search_results: Dict[str, List[SearchResult]]
    ) -> EnhancedUserProfile:
        """Enhance user profile with AI-extracted information"""
        
        # Flatten all search results
        all_results = []
        for results in search_results.values():
            all_results.extend(results)
        
        # Extract interests
        ai_interests = await self.extract_interests_with_ai(all_results, user_profile)
        
        # Add to profile
        for interest in ai_interests:
            user_profile.add_interest(interest)
        
        # Extract additional demographics if available
        if self.config.use_openai:
            demographics = await self._infer_demographics(all_results, user_profile)
            user_profile.inferred_demographics.update(demographics)
        
        return user_profile
    
    async def _infer_demographics(
        self,
        results: List[SearchResult],
        user_profile: EnhancedUserProfile
    ) -> Dict[str, Any]:
        """Infer demographic information"""
        demographics = {}
        
        if not self.config.use_openai:
            return demographics
        
        try:
            context = self._prepare_context(results, user_profile)
            
            prompt = f"""
            Based on the following information, infer any demographic details about {user_profile.full_name}.
            Only include information that can be reasonably inferred from the data.
            
            Context:
            {context}
            
            Return as JSON with any of these fields (only if confident):
            - age_range: string (e.g., "20-30")
            - profession: string
            - education_level: string
            - relationship_status: string
            - has_children: boolean
            - pet_owner: boolean
            - income_bracket: string
            
            Be conservative and only include fields you're reasonably confident about.
            """
            
            response = await openai.ChatCompletion.acreate(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at inferring demographics from limited information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            import json
            demographics = json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Demographic inference failed: {e}")
        
        return demographics


# services/eventbrite_service.py
"""
Eventbrite API integration for finding local events
"""
import requests
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


@dataclass
class EventbriteEvent:
    """Eventbrite event data structure"""
    id: str
    name: str
    description: str
    url: str
    start_time: datetime
    end_time: datetime
    venue_name: str
    venue_address: str
    latitude: float
    longitude: float
    category: str
    subcategory: str
    is_free: bool
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    image_url: str = ""
    organizer: str = ""
    capacity: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'venue_name': self.venue_name,
            'venue_address': self.venue_address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'category': self.category,
            'subcategory': self.subcategory,
            'is_free': self.is_free,
            'price_min': self.price_min,
            'price_max': self.price_max,
            'image_url': self.image_url,
            'organizer': self.organizer,
            'capacity': self.capacity
        }
    
    def get_distance_from(self, lat: float, lon: float) -> float:
        """Calculate distance in miles from given coordinates"""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat)
        lon1_rad = math.radians(lon)
        lat2_rad = math.radians(self.latitude)
        lon2_rad = math.radians(self.longitude)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


class EventbriteService:
    """Service for interacting with Eventbrite API"""
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        Initialize Eventbrite service
        
        Args:
            api_key: Eventbrite API key (OAuth token)
            config: Configuration dictionary
        """
        self.api_key = api_key
        self.config = config or {}
        self.base_url = "https://www.eventbriteapi.com/v3"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    def search_events(
        self,
        location: Dict[str, Any],
        interests: List[str],
        radius_miles: int = 50,
        time_range_hours: int = 12
    ) -> List[EventbriteEvent]:
        """
        Search for events based on location and interests
        
        Args:
            location: Dict with latitude, longitude, city
            interests: List of user interests/keywords
            radius_miles: Search radius in miles
            time_range_hours: Time range for events
            
        Returns:
            List of EventbriteEvent objects
        """
        if not self.api_key:
            logger.warning("Eventbrite API key not provided")
            return []
        
        events = []
        
        try:
            # Search by location
            location_events = self._search_by_location(
                location['latitude'],
                location['longitude'],
                radius_miles,
                time_range_hours
            )
            events.extend(location_events)
            
            # Search by interests
            for interest in interests[:5]:  # Limit to 5 interests
                interest_events = self._search_by_keyword(
                    interest,
                    location['latitude'],
                    location['longitude'],
                    radius_miles,
                    time_range_hours
                )
                events.extend(interest_events)
            
            # Remove duplicates
            unique_events = {event.id: event for event in events}
            events = list(unique_events.values())
            
            # Filter by distance and time
            filtered_events = self._filter_events(
                events,
                location['latitude'],
                location['longitude'],
                radius_miles,
                time_range_hours
            )
            
            # Sort by start time
            filtered_events.sort(key=lambda e: e.start_time)
            
            # Limit results
            max_events = self.config.get('MAX_EVENTS', 30)
            return filtered_events[:max_events]
            
        except Exception as e:
            logger.error(f"Error searching Eventbrite events: {e}")
            return []
    
    def _search_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_miles: int,
        time_range_hours: int
    ) -> List[EventbriteEvent]:
        """Search events by location"""
        events = []
        
        # Calculate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(hours=time_range_hours)
        
        params = {
            "location.latitude": latitude,
            "location.longitude": longitude,
            "location.within": f"{radius_miles}mi",
            "start_date.range_start": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "start_date.range_end": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "expand": "venue,category,ticket_availability",
            "status": "live"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/events/search/",
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                events = self._parse_events(data.get('events', []))
            else:
                logger.error(f"Eventbrite API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error searching Eventbrite by location: {e}")
        
        return events
    
    def _search_by_keyword(
        self,
        keyword: str,
        latitude: float,
        longitude: float,
        radius_miles: int,
        time_range_hours: int
    ) -> List[EventbriteEvent]:
        """Search events by keyword"""
        events = []
        
        # Calculate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(hours=time_range_hours)
        
        params = {
            "q": keyword,
            "location.latitude": latitude,
            "location.longitude": longitude,
            "location.within": f"{radius_miles}mi",
            "start_date.range_start": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "start_date.range_end": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "expand": "venue,category,ticket_availability",
            "status": "live"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/events/search/",
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                events = self._parse_events(data.get('events', []))
            else:
                logger.error(f"Eventbrite API error for keyword '{keyword}': {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error searching Eventbrite by keyword '{keyword}': {e}")
        
        return events
    
    def _parse_events(self, events_data: List[Dict[str, Any]]) -> List[EventbriteEvent]:
        """Parse events from API response"""
        events = []
        
        for event_data in events_data:
            try:
                event = self._parse_single_event(event_data)
                if event:
                    events.append(event)
            except Exception as e:
                logger.debug(f"Error parsing event: {e}")
                continue
        
        return events
    
    def _parse_single_event(self, event_data: Dict[str, Any]) -> Optional[EventbriteEvent]:
        """Parse a single event from API response"""
        try:
            # Basic info
            event_id = event_data.get('id', '')
            name = event_data.get('name', {}).get('text', 'Unknown Event')
            description = event_data.get('description', {}).get('text', '')[:500]
            url = event_data.get('url', '')
            
            # Time info
            start = event_data.get('start', {})
            end = event_data.get('end', {})
            
            start_time = datetime.fromisoformat(start.get('local', '').replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.get('local', '').replace('Z', '+00:00'))
            
            # Venue info
            venue = event_data.get('venue', {})
            if not venue:
                return None
                
            venue_name = venue.get('name', 'Unknown Venue')
            
            address_parts = []
            address = venue.get('address', {})
            if address.get('address_1'):
                address_parts.append(address['address_1'])
            if address.get('city'):
                address_parts.append(address['city'])
            if address.get('region'):
                address_parts.append(address['region'])
                
            venue_address = ', '.join(address_parts)
            
            latitude = float(venue.get('latitude', 0))
            longitude = float(venue.get('longitude', 0))
            
            if not latitude or not longitude:
                return None
            
            # Category
            category_data = event_data.get('category', {})
            category = category_data.get('name', 'Other')
            subcategory = event_data.get('subcategory', {}).get('name', '')
            
            # Pricing
            is_free = event_data.get('is_free', False)
            
            price_min = None
            price_max = None
            
            if not is_free:
                ticket_availability = event_data.get('ticket_availability', {})
                if ticket_availability.get('minimum_ticket_price'):
                    price_min = float(ticket_availability['minimum_ticket_price']['major_value'])
                if ticket_availability.get('maximum_ticket_price'):
                    price_max = float(ticket_availability['maximum_ticket_price']['major_value'])
            
            # Image
            logo = event_data.get('logo', {})
            image_url = logo.get('url', '') if logo else ''
            
            # Organizer
            organizer = event_data.get('organizer', {}).get('name', '')
            
            # Capacity
            capacity = event_data.get('capacity', None)
            
            return EventbriteEvent(
                id=event_id,
                name=name,
                description=description,
                url=url,
                start_time=start_time,
                end_time=end_time,
                venue_name=venue_name,
                venue_address=venue_address,
                latitude=latitude,
                longitude=longitude,
                category=category,
                subcategory=subcategory,
                is_free=is_free,
                price_min=price_min,
                price_max=price_max,
                image_url=image_url,
                organizer=organizer,
                capacity=capacity
            )
            
        except Exception as e:
            logger.error(f"Error parsing event data: {e}")
            return None
    
    def _filter_events(
        self,
        events: List[EventbriteEvent],
        latitude: float,
        longitude: float,
        radius_miles: int,
        time_range_hours: int
    ) -> List[EventbriteEvent]:
        """Filter events by distance and time"""
        filtered = []
        
        now = datetime.now()
        max_time = now + timedelta(hours=time_range_hours)
        
        for event in events:
            # Check time range
            if event.start_time < now or event.start_time > max_time:
                continue
            
            # Check distance
            distance = event.get_distance_from(latitude, longitude)
            if distance > radius_miles:
                continue
            
            filtered.append(event)
        
        return filtered
    
    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific event"""
        try:
            response = requests.get(
                f"{self.base_url}/events/{event_id}/",
                headers=self.headers,
                params={"expand": "venue,category,organizer,ticket_classes"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error fetching event details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return None
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all available event categories"""
        try:
            response = requests.get(
                f"{self.base_url}/categories/",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('categories', [])
            else:
                logger.error(f"Error fetching categories: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
