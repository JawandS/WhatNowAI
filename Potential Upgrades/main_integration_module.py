# searchmethods/enhanced_search.py
"""
Enhanced search integration module that combines all search capabilities
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from concurrent.futures import ThreadPoolExecutor
import json

from .core import (
    EnhancedUserProfile, SearchOrchestrator, DataSource,
    SearchResult, UserInterest
)
from .core.data_processor import InterestExtractor, DataFilter
from .scrapers.web_scrapers import (
    GoogleSearchScraper, LinkedInScraper, TwitterScraper,
    InstagramScraper, GitHubScraper, RedditScraper,
    NewsArchiveScraper
)
from .ai.ai_processor import AIProcessor, AIConfig
from ..services.eventbrite_service import EventbriteService
from ..services.mapping_service import MappingService
from ..config.settings import (
    SEARCH_CONFIG, AI_CONFIG, EVENTBRITE_CONFIG,
    EVENTBRITE_API_KEY, OPENAI_API_KEY
)

logger = logging.getLogger(__name__)


class EnhancedSearchSystem:
    """Main search system that orchestrates all components"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the enhanced search system"""
        self.config = config or SEARCH_CONFIG
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize all search components"""
        logger.info("Initializing Enhanced Search System...")
        
        # Initialize scrapers
        scraper_config = self.config.get('scrapers', {})
        self.scrapers = [
            GoogleSearchScraper(scraper_config),
            LinkedInScraper(scraper_config),
            TwitterScraper(scraper_config),
            InstagramScraper(scraper_config),
            GitHubScraper(scraper_config),
            RedditScraper(scraper_config),
            NewsArchiveScraper(scraper_config)
        ]
        
        # Initialize search orchestrator
        self.orchestrator = SearchOrchestrator(
            modules=self.scrapers,
            config=self.config.get('orchestrator', {})
        )
        
        # Initialize data processors
        self.interest_extractor = InterestExtractor(
            config=self.config.get('interest_extraction', {})
        )
        self.data_filter = DataFilter(
            config=self.config.get('data_filtering', {})
        )
        
        # Initialize AI processor (optional)
        ai_config = AIConfig(
            use_openai=bool(OPENAI_API_KEY),
            openai_api_key=OPENAI_API_KEY,
            **AI_CONFIG
        )
        self.ai_processor = AIProcessor(ai_config) if ai_config.use_openai or ai_config.use_huggingface else None
        
        # Initialize Eventbrite service
        self.eventbrite_service = EventbriteService(
            api_key=EVENTBRITE_API_KEY,
            config=EVENTBRITE_CONFIG
        ) if EVENTBRITE_API_KEY else None
        
        logger.info("Enhanced Search System initialized successfully")
    
    async def perform_enhanced_search(
        self,
        first_name: str,
        last_name: str,
        location: Dict[str, Any],
        activity: str,
        social_handles: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive search and analysis
        
        Args:
            first_name: User's first name
            last_name: User's last name
            location: Location data with lat/lon and city
            activity: What the user wants to do
            social_handles: Optional social media handles
            
        Returns:
            Dictionary with search results, interests, and events
        """
        start_time = datetime.now()
        
        # Create user profile
        user_profile = EnhancedUserProfile(
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            location=location,
            activity=activity,
            social_profiles=social_handles or {}
        )
        
        logger.info(f"Starting enhanced search for {user_profile.full_name}")
        
        try:
            # Step 1: Perform web searches
            search_results = await self._perform_searches(user_profile)
            
            # Step 2: Filter and validate results
            filtered_results = await self._filter_results(search_results, user_profile)
            
            # Step 3: Extract interests
            interests = await self._extract_interests(filtered_results, user_profile)
            
            # Step 4: Enhance with AI if available
            if self.ai_processor:
                user_profile = await self.ai_processor.enhance_profile_with_ai(
                    user_profile, filtered_results
                )
            
            # Step 5: Find events based on interests
            events = await self._find_events(user_profile)
            
            # Calculate timing
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # Prepare response
            response = {
                'success': True,
                'user_profile': user_profile.to_dict(),
                'search_results': self._summarize_results(filtered_results),
                'interests': [interest.to_dict() for interest in user_profile.get_top_interests(10)],
                'events': events,
                'metadata': {
                    'search_time_seconds': elapsed_time,
                    'total_results_found': user_profile.total_results_found,
                    'data_sources_used': [ds.value for ds in user_profile.data_sources_used],
                    'ai_enhanced': self.ai_processor is not None,
                    'eventbrite_enabled': self.eventbrite_service is not None
                }
            }
            
            logger.info(f"Enhanced search completed in {elapsed_time:.2f} seconds")
            return response
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_profile': user_profile.to_dict(),
                'search_results': {},
                'interests': [],
                'events': []
            }
    
    async def _perform_searches(
        self, 
        user_profile: EnhancedUserProfile
    ) -> Dict[DataSource, List[SearchResult]]:
        """Perform all searches in parallel"""
        logger.info("Starting parallel searches...")
        
        # Use orchestrator to run all searches
        results = await self.orchestrator.search_all(user_profile)
        
        logger.info(f"Search complete. Found results from {len(results)} sources")
        return results
    
    async def _filter_results(
        self,
        search_results: Dict[DataSource, List[SearchResult]],
        user_profile: EnhancedUserProfile
    ) -> Dict[DataSource, List[SearchResult]]:
        """Filter and validate search results"""
        logger.info("Filtering search results...")
        
        filtered = {}
        
        for source, results in search_results.items():
            # Apply data filter
            filtered_source_results = self.data_filter.filter_results(results, user_profile)
            
            if filtered_source_results:
                filtered[source] = filtered_source_results
                logger.info(f"{source.value}: {len(filtered_source_results)} relevant results")
        
        return filtered
    
    async def _extract_interests(
        self,
        search_results: Dict[DataSource, List[SearchResult]],
        user_profile: EnhancedUserProfile
    ) -> List[UserInterest]:
        """Extract user interests from search results"""
        logger.info("Extracting user interests...")
        
        all_results = []
        for results in search_results.values():
            all_results.extend(results)
        
        # Use traditional extraction
        interests = self.interest_extractor.extract_interests(all_results)
        
        # Add interests to profile
        for interest in interests:
            user_profile.add_interest(interest)
        
        # Enhance with AI if available
        if self.ai_processor:
            ai_interests = await self.ai_processor.extract_interests_with_ai(
                all_results, user_profile
            )
            for interest in ai_interests:
                user_profile.add_interest(interest)
        
        logger.info(f"Extracted {len(user_profile.interests)} total interests")
        return user_profile.interests
    
    async def _find_events(self, user_profile: EnhancedUserProfile) -> List[Dict[str, Any]]:
        """Find events based on user profile and interests"""
        logger.info("Finding events based on interests...")
        
        events = []
        
        if not self.eventbrite_service:
            logger.warning("Eventbrite service not available")
            return events
        
        # Get top interest keywords
        interest_keywords = []
        for interest in user_profile.get_top_interests(5):
            interest_keywords.extend(interest.keywords[:2])
        
        # Add activity keywords
        if user_profile.activity:
            interest_keywords.extend(user_profile.activity.split()[:3])
        
        # Remove duplicates
        interest_keywords = list(set(interest_keywords))
        
        # Search for events
        eventbrite_events = self.eventbrite_service.search_events(
            location=user_profile.location,
            interests=interest_keywords,
            radius_miles=50,
            time_range_hours=12
        )
        
        # Convert to dict format
        for event in eventbrite_events:
            events.append(event.to_dict())
        
        logger.info(f"Found {len(events)} relevant events")
        return events
    
    def _summarize_results(
        self, 
        search_results: Dict[DataSource, List[SearchResult]]
    ) -> Dict[str, Any]:
        """Create summary of search results"""
        summary = {}
        
        for source, results in search_results.items():
            source_name = source.value
            
            # Get top results
            top_results = []
            for result in results[:3]:  # Top 3 per source
                top_results.append({
                    'title': result.title,
                    'url': result.url,
                    'relevance': result.relevance_score,
                    'snippet': result.content[:200] + '...' if len(result.content) > 200 else result.content
                })
            
            summary[source_name] = {
                'total_results': len(results),
                'top_results': top_results
            }
        
        return summary
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up search system resources...")
        
        # Cleanup scrapers
        for scraper in self.scrapers:
            if hasattr(scraper, 'cleanup'):
                await scraper.cleanup()
        
        logger.info("Cleanup complete")


# Enhanced version of the original background_search function
async def perform_enhanced_background_search(user_profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced version of the background search that uses all new capabilities
    
    Args:
        user_profile_data: Dictionary with user information
        
    Returns:
        Comprehensive search results with interests and events
    """
    # Extract data
    names = user_profile_data.get('name', '').split(' ', 1)
    first_name = names[0] if names else ''
    last_name = names[1] if len(names) > 1 else ''
    
    location_str = user_profile_data.get('location', '')
    location_parts = location_str.split(',')
    
    location = {
        'city': location_parts[0].strip() if location_parts else '',
        'state': location_parts[1].strip() if len(location_parts) > 1 else '',
        'country': location_parts[2].strip() if len(location_parts) > 2 else 'US',
        'latitude': user_profile_data.get('latitude'),
        'longitude': user_profile_data.get('longitude')
    }
    
    activity = user_profile_data.get('activity', '')
    social_handles = user_profile_data.get('social_handles', {})
    
    # Initialize search system
    search_system = EnhancedSearchSystem()
    
    try:
        # Perform search
        results = await search_system.perform_enhanced_search(
            first_name=first_name,
            last_name=last_name,
            location=location,
            activity=activity,
            social_handles=social_handles
        )
        
        return results
        
    finally:
        # Cleanup
        await search_system.cleanup()


# Update the existing routes.py to use enhanced search
def integrate_enhanced_search(app):
    """
    Integration function to update existing Flask routes
    
    This function should be called in your app.py to integrate
    the enhanced search functionality
    """
    from flask import current_app
    
    # Import the enhanced search
    from searchmethods.enhanced_search import perform_enhanced_background_search
    
    # Replace the existing perform_background_search function
    import searchmethods.background_search
    
    # Monkey patch with async wrapper
    def enhanced_wrapper(user_profile):
        """Wrapper to run async function in sync context"""
        import asyncio
        
        user_data = {
            'name': user_profile.name,
            'location': user_profile.location,
            'social_handles': user_profile.social_handles,
            'activity': user_profile.activity
        }
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                perform_enhanced_background_search(user_data)
            )
            
            # Convert to expected format
            return {
                'raw_results': result.get('search_results', {}),
                'summaries': {
                    'general': f"Found {result['metadata']['total_results_found']} results about {user_profile.name}",
                    'social': f"Analyzed {len(result['user_profile']['social_profiles'])} social media profiles",
                    'location': f"Found {len(result.get('events', []))} local events in {user_profile.location}",
                    'activity': f"Discovered {len(result.get('interests', []))} interests related to {user_profile.activity}"
                },
                'total_results': result['metadata']['total_results_found'],
                'interests': result.get('interests', []),
                'events': result.get('events', [])
            }
            
        finally:
            loop.close()
    
    # Replace the function
    searchmethods.background_search.perform_background_search = enhanced_wrapper
    
    logger.info("Enhanced search integrated successfully")


# Setup and configuration instructions
SETUP_INSTRUCTIONS = """
Enhanced Search System Setup Instructions
=========================================

1. Install Required Dependencies:
   ```bash
   pip install aiohttp beautifulsoup4 selenium cloudscraper fake-useragent
   pip install nltk scikit-learn numpy
   pip install openai transformers sentence-transformers torch
   pip install requests python-dateutil
   ```

2. Download NLTK Data:
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   nltk.download('wordnet')
   nltk.download('averaged_perceptron_tagger')
   ```

3. Set Environment Variables:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"  # Optional
   export EVENTBRITE_API_KEY="your-eventbrite-oauth-token"  # Required for events
   export HUGGINGFACE_API_KEY="your-hf-api-key"  # Optional
   ```

4. Update config/settings.py:
   ```python
   # Add these configurations
   SEARCH_CONFIG = {
       'scrapers': {
           'use_selenium': False,  # Set to True if you have Chrome/Chromium
           'rate_limit': 1,  # Requests per second
       },
       'orchestrator': {
           'max_workers': 10,
       },
       'interest_extraction': {
           'min_interest_score': 0.3,
       },
       'data_filtering': {
           'min_relevance_score': 0.5,
       }
   }
   
   AI_CONFIG = {
       'use_huggingface': True,
       'hf_model': 'facebook/bart-large-mnli',
       'use_local_embeddings': True,
       'embedding_model': 'all-MiniLM-L6-v2'
   }
   
   EVENTBRITE_CONFIG = {
       'MAX_EVENTS': 30,
       'BASE_URL': 'https://www.eventbriteapi.com/v3'
   }
   ```

5. Update your app.py:
   ```python
   from searchmethods.enhanced_search import integrate_enhanced_search
   
   def create_app():
       app = Flask(__name__)
       
       # ... existing code ...
       
       # Integrate enhanced search
       with app.app_context():
           integrate_enhanced_search(app)
       
       return app
   ```

6. For Selenium Support (Optional):
   - Install Chrome/Chromium browser
   - Install ChromeDriver: https://chromedriver.chromium.org/
   - Add to PATH or specify in config

7. API Keys:
   - Eventbrite: Get OAuth token from https://www.eventbrite.com/platform/api
   - OpenAI: Get from https://platform.openai.com/api-keys
   - HuggingFace: Get from https://huggingface.co/settings/tokens

8. Privacy and Ethics:
   - Always respect user privacy
   - Only search publicly available information
   - Implement rate limiting to avoid overloading services
   - Consider GDPR and data protection regulations
   - Get user consent for data collection

9. Performance Optimization:
   - Use caching for repeated searches
   - Implement result pagination
   - Consider using Redis for distributed caching
   - Monitor API usage and costs

10. Error Handling:
    - All modules include comprehensive error handling
    - Check logs in 'logs/' directory
    - Monitor rate limit errors
    - Implement retry logic for transient failures
"""

# Save setup instructions
def save_setup_instructions():
    """Save setup instructions to file"""
    with open('ENHANCED_SEARCH_SETUP.md', 'w') as f:
        f.write(SETUP_INSTRUCTIONS)
    print("Setup instructions saved to ENHANCED_SEARCH_SETUP.md")


if __name__ == "__main__":
    # Save setup instructions
    save_setup_instructions()
    
    # Test the system
    import asyncio
    
    async def test_system():
        """Test the enhanced search system"""
        system = EnhancedSearchSystem()
        
        result = await system.perform_enhanced_search(
            first_name="John",
            last_name="Doe",
            location={
                'city': 'San Francisco',
                'state': 'CA',
                'country': 'US',
                'latitude': 37.7749,
                'longitude': -122.4194
            },
            activity="learn photography",
            social_handles={
                'twitter': 'johndoe',
                'instagram': 'johndoe_photos'
            }
        )
        
        print(json.dumps(result, indent=2))
        
        await system.cleanup()
    
    # Run test
    asyncio.run(test_system())
