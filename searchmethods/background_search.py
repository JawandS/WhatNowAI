"""
Background search service for gathering user and location context
Uses web scraping and search engines to find relevant information
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin, urlparse
import json
import re
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile data structure"""
    name: str
    location: str = ""
    social_handles: Dict[str, str] = None
    activity: str = ""
    
    def __post_init__(self):
        if self.social_handles is None:
            self.social_handles = {}


@dataclass
class SearchResult:
    """Search result data structure"""
    source: str
    title: str
    url: str
    content: str
    relevance_score: float = 0.0
    timestamp: str = ""


class BackgroundSearchService:
    """Service for performing background searches on user information"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the background search service
        
        Args:
            config: Configuration dictionary with search parameters
        """
        from config.settings import SEARCH_CONFIG
        
        self.config = config or SEARCH_CONFIG
        self.session = None
        self.results_cache = {}
        
    def _setup_session(self) -> requests.Session:
        """Setup requests session with retries and proper headers"""
        session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Updated parameter name
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'User-Agent': self.config.get('USER_AGENT', 'WhatNowAI/1.0'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def search_user_info(self, user_profile: UserProfile) -> Dict[str, List[SearchResult]]:
        """
        Search for information about the user focusing only on social media and local activities
        
        Args:
            user_profile: User profile containing name, location, social handles, etc.
            
        Returns:
            Dictionary of search results organized by source
        """
        logger.info(f"Starting focused search for user: {user_profile.name}")
        
        results = {
            'general': [],  # Will remain empty - no general searches
            'social': [],
            'location': [],
            'activity': []
        }
        
        if not self.session:
            self.session = self._setup_session()
        
        import time
        start_time = time.time()
        search_timeout = 10  # 10 second limit
        
        try:
            # Only search social media platforms if handles are provided
            if user_profile.social_handles:
                # Check if we still have time
                if time.time() - start_time < search_timeout:
                    social_results = self._search_social_media(user_profile.social_handles)
                    results['social'].extend(social_results)
                    logger.info(f"Found {len(social_results)} social media results")
            
            # Search location-specific information if we have time
            if user_profile.location and (time.time() - start_time < search_timeout):
                location_results = self._search_location_info(user_profile.location, user_profile.activity)
                results['location'].extend(location_results)
                logger.info(f"Found {len(location_results)} location results")
            
            # Search activity-related information if we have time
            if user_profile.activity and (time.time() - start_time < search_timeout):
                activity_results = self._search_activity_info(user_profile.activity, user_profile.location)
                results['activity'].extend(activity_results)
                logger.info(f"Found {len(activity_results)} activity results")
            
            # Log if we hit the timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= search_timeout:
                logger.warning(f"Search timeout reached ({elapsed_time:.1f}s), returning partial results")
            else:
                logger.info(f"Search completed in {elapsed_time:.1f}s")
                
        except Exception as e:
            logger.error(f"Error during focused search: {str(e)}")
        
        return results
    
    def _search_general_info(self, name: str) -> List[SearchResult]:
        """Search for specific information about this person (not celebrities)"""
        results = []
        
        # Focus on finding the actual user, not celebrities with the same name
        # Use more specific search terms to filter out famous people
        specific_queries = [
            f'"{name}" -wikipedia -celebrity -famous -actor -singer -politician',
            f'"{name}" profile personal',
            f'"{name}" professional background'
        ]
        
        # Use DuckDuckGo for privacy-focused search
        for query in specific_queries:
            encoded_query = quote_plus(query)
            search_urls = [
                f"https://duckduckgo.com/html/?q={encoded_query}",
            ]
            
            for url in search_urls:
                try:
                    response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
                    if response.status_code == 200:
                        search_results = self._parse_search_results(response.text, 'general')
                        # Filter out celebrity/famous person results
                        filtered_results = [r for r in search_results if not self._is_celebrity_result(r)]
                        results.extend(filtered_results[:3])  # Limit to 3 per query
                        time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Failed to search {url}: {str(e)}")
                    continue
        
        return results[:self.config.get('MAX_RESULTS_PER_SOURCE', 8)]
    
    def _is_celebrity_result(self, result: SearchResult) -> bool:
        """Check if a search result is about a celebrity/famous person"""
        celebrity_keywords = [
            'wikipedia', 'celebrity', 'famous', 'actor', 'actress', 'singer', 
            'musician', 'politician', 'athlete', 'sports', 'movie', 'film',
            'album', 'song', 'tv show', 'series', 'biography', 'born in',
            'filmography', 'discography', 'awards', 'grammy', 'oscar', 'emmy'
        ]
        
        content_lower = result.content.lower()
        title_lower = result.title.lower()
        
        return any(keyword in content_lower or keyword in title_lower for keyword in celebrity_keywords)
    
    def _search_social_media(self, social_handles: Dict[str, str]) -> List[SearchResult]:
        """Search social media platforms for user information - fast and focused"""
        results = []
        start_time = time.time()
        timeout_per_platform = 2  # Max 2 seconds per platform
        
        for platform, handle in social_handles.items():
            if not handle:
                continue
            
            # Check timeout
            if time.time() - start_time > 8:  # Reserve 2 seconds for other searches
                logger.warning("Social media search timeout reached, skipping remaining platforms")
                break
                
            try:
                platform_start = time.time()
                
                if platform.lower() == 'github':
                    # GitHub API is fastest, prioritize it
                    platform_results = self._search_github_info(handle)
                    results.extend(platform_results)
                elif platform.lower() in ['twitter', 'linkedin', 'instagram', 'tiktok', 'youtube']:
                    # Quick search for other platforms
                    platform_results = self._quick_social_search(platform, handle)
                    results.extend(platform_results)
                
                # Check if this platform took too long
                if time.time() - platform_start > timeout_per_platform:
                    logger.warning(f"{platform} search took too long, skipping remaining platforms")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to search {platform} for {handle}: {str(e)}")
                continue
        
        return results[:self.config.get('MAX_RESULTS_PER_SOURCE', 3)]
    
    def _quick_social_search(self, platform: str, handle: str) -> List[SearchResult]:
        """Quick search for social media platforms with minimal processing"""
        results = []
        
        try:
            # Simple site-specific search
            query = quote_plus(f"site:{platform}.com {handle}")
            url = f"https://duckduckgo.com/html/?q={query}"
            
            response = self.session.get(url, timeout=3)  # Short timeout
            if response.status_code == 200:
                # Quick parse - just get first few results
                soup = BeautifulSoup(response.text, 'html.parser')
                result_elements = soup.find_all('div', class_='result')[:2]  # Max 2 results
                
                for element in result_elements:
                    try:
                        title_elem = element.find('a', class_='result__a')
                        snippet_elem = element.find('a', class_='result__snippet')
                        
                        if title_elem and snippet_elem:
                            result = SearchResult(
                                source='social',
                                title=title_elem.get_text(strip=True)[:100],  # Truncate for speed
                                url=title_elem.get('href', ''),
                                content=snippet_elem.get_text(strip=True)[:200],  # Truncate for speed
                                relevance_score=0.7
                            )
                            results.append(result)
                    except:
                        continue
                        
        except Exception as e:
            logger.warning(f"Quick search failed for {platform}: {str(e)}")
        
        return results
    
    def _search_location_info(self, location: str, activity: str = "") -> List[SearchResult]:
        """Fast search for location-specific activities"""
        results = []
        
        if not self.config.get('LOCAL_ACTIVITY_SEARCH', True):
            return results
        
        # Limit to most important queries for speed
        queries = [
            f"things to do {location} today",
        ]
        
        # Add one activity-specific query if provided
        if activity:
            queries.append(f"{activity} {location} classes")
        
        for query in queries[:2]:  # Max 2 queries for speed
            try:
                encoded_query = quote_plus(query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=self.config.get('TIMEOUT', 5))
                if response.status_code == 200:
                    search_results = self._quick_parse_results(response.text, 'location')
                    results.extend(search_results[:2])  # Max 2 per query
                    
            except Exception as e:
                logger.warning(f"Failed location search for {query}: {str(e)}")
                continue
        
        return results[:self.config.get('MAX_RESULTS_PER_SOURCE', 3)]
    
    def _search_activity_info(self, activity: str, location: str = "") -> List[SearchResult]:
        """Fast search for activity-related information"""
        results = []
        
        # Limit to essential queries for speed
        queries = [
            f"how to get started with {activity}",
        ]
        
        # Add location-specific query if provided
        if location:
            queries.append(f"{activity} beginner guide {location}")
        
        for query in queries[:2]:  # Max 2 queries for speed
            try:
                encoded_query = quote_plus(query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=self.config.get('TIMEOUT', 5))
                if response.status_code == 200:
                    search_results = self._quick_parse_results(response.text, 'activity')
                    results.extend(search_results[:2])  # Max 2 per query
                    
            except Exception as e:
                logger.warning(f"Failed activity search for {query}: {str(e)}")
                continue
        
        return results[:self.config.get('MAX_RESULTS_PER_SOURCE', 3)]
    
    def _quick_parse_results(self, html_content: str, source_type: str) -> List[SearchResult]:
        """Fast parsing of search results with minimal processing"""
        results = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result_elements = soup.find_all('div', class_='result')[:3]  # Max 3 for speed
            
            for element in result_elements:
                try:
                    title_elem = element.find('a', class_='result__a')
                    snippet_elem = element.find('a', class_='result__snippet')
                    
                    if title_elem and snippet_elem:
                        result = SearchResult(
                            source=source_type,
                            title=title_elem.get_text(strip=True)[:80],  # Truncate for speed
                            url=title_elem.get('href', ''),
                            content=snippet_elem.get_text(strip=True)[:150],  # Truncate for speed
                            relevance_score=0.5
                        )
                        results.append(result)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Quick parse failed: {str(e)}")
        
        return results
    
    def _search_twitter_info(self, handle: str) -> List[SearchResult]:
        """Search for Twitter profile information (public data only)"""
        results = []
        
        # Search for public information about the Twitter handle
        query = quote_plus(f"site:twitter.com {handle}")
        url = f"https://duckduckgo.com/html/?q={query}"
        
        try:
            response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
            if response.status_code == 200:
                results = self._parse_search_results(response.text, 'social')
        except Exception as e:
            logger.warning(f"Failed to search Twitter info for {handle}: {str(e)}")
        
        return results
    
    def _search_linkedin_info(self, handle: str) -> List[SearchResult]:
        """Search for LinkedIn profile information (public data only)"""
        results = []
        
        # Search for public LinkedIn information
        query = quote_plus(f"site:linkedin.com {handle}")
        url = f"https://duckduckgo.com/html/?q={query}"
        
        try:
            response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
            if response.status_code == 200:
                results = self._parse_search_results(response.text, 'social')
        except Exception as e:
            logger.warning(f"Failed to search LinkedIn info for {handle}: {str(e)}")
        
        return results
    
    def _search_github_info(self, handle: str) -> List[SearchResult]:
        """Search for GitHub profile information using GitHub API"""
        results = []
        
        try:
            # Try to get public GitHub profile information
            api_url = f"https://api.github.com/users/{handle}"
            response = self.session.get(api_url, timeout=self.config.get('TIMEOUT', 30))
            
            if response.status_code == 200:
                data = response.json()
                
                # Create a search result from GitHub profile
                result = SearchResult(
                    source='github',
                    title=f"GitHub Profile: {data.get('name', handle)}",
                    url=data.get('html_url', f"https://github.com/{handle}"),
                    content=f"Bio: {data.get('bio', 'No bio available')}. "
                           f"Public repos: {data.get('public_repos', 0)}. "
                           f"Followers: {data.get('followers', 0)}. "
                           f"Location: {data.get('location', 'Not specified')}.",
                    relevance_score=0.8
                )
                results.append(result)
                
        except Exception as e:
            logger.warning(f"Failed to search GitHub info for {handle}: {str(e)}")
        
        return results
    
    def _search_instagram_info(self, handle: str) -> List[SearchResult]:
        """Search for Instagram profile information (public data only)"""
        results = []
        
        # Search for public Instagram information
        query = quote_plus(f"site:instagram.com {handle}")
        url = f"https://duckduckgo.com/html/?q={query}"
        
        try:
            response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
            if response.status_code == 200:
                results = self._parse_search_results(response.text, 'social')
        except Exception as e:
            logger.warning(f"Failed to search Instagram info for {handle}: {str(e)}")
        
        return results
    
    def _search_tiktok_info(self, handle: str) -> List[SearchResult]:
        """Search for TikTok profile information (public data only)"""
        results = []
        
        # Search for public TikTok information
        query = quote_plus(f"site:tiktok.com @{handle}")
        url = f"https://duckduckgo.com/html/?q={query}"
        
        try:
            response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
            if response.status_code == 200:
                results = self._parse_search_results(response.text, 'social')
        except Exception as e:
            logger.warning(f"Failed to search TikTok info for {handle}: {str(e)}")
        
        return results
    
    def _search_youtube_info(self, handle: str) -> List[SearchResult]:
        """Search for YouTube channel information (public data only)"""
        results = []
        
        # Search for public YouTube information
        queries = [
            quote_plus(f"site:youtube.com {handle}"),
            quote_plus(f"site:youtube.com/c/{handle}"),
            quote_plus(f"site:youtube.com/@{handle}")
        ]
        
        for query in queries:
            try:
                url = f"https://duckduckgo.com/html/?q={query}"
                response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
                if response.status_code == 200:
                    search_results = self._parse_search_results(response.text, 'social')
                    results.extend(search_results[:2])
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"Failed to search YouTube info for {handle}: {str(e)}")
                continue
        
        return results

    def _parse_search_results(self, html_content: str, source_type: str) -> List[SearchResult]:
        """Parse HTML search results and extract relevant information"""
        results = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Parse DuckDuckGo results
            if 'duckduckgo.com' in html_content or 'ddg' in html_content:
                results.extend(self._parse_duckduckgo_results(soup, source_type))
            # Parse Bing results
            elif 'bing.com' in html_content:
                results.extend(self._parse_bing_results(soup, source_type))
                
        except Exception as e:
            logger.warning(f"Failed to parse search results: {str(e)}")
        
        return results
    
    def _parse_duckduckgo_results(self, soup: BeautifulSoup, source_type: str) -> List[SearchResult]:
        """Parse DuckDuckGo search results"""
        results = []
        
        # Find result elements (DuckDuckGo HTML structure)
        result_elements = soup.find_all('div', class_='result')
        
        for element in result_elements[:self.config.get('MAX_RESULTS_PER_SOURCE', 10)]:
            try:
                title_elem = element.find('a', class_='result__a')
                snippet_elem = element.find('a', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    content = snippet_elem.get_text(strip=True)
                    
                    if title and url and content:
                        result = SearchResult(
                            source=source_type,
                            title=title,
                            url=url,
                            content=content,
                            relevance_score=0.5
                        )
                        results.append(result)
                        
            except Exception as e:
                logger.warning(f"Failed to parse individual result: {str(e)}")
                continue
        
        return results
    
    def _parse_bing_results(self, soup: BeautifulSoup, source_type: str) -> List[SearchResult]:
        """Parse Bing search results"""
        results = []
        
        # Find result elements (Bing HTML structure)
        result_elements = soup.find_all('li', class_='b_algo')
        
        for element in result_elements[:self.config.get('MAX_RESULTS_PER_SOURCE', 10)]:
            try:
                title_elem = element.find('h2')
                if title_elem:
                    title_link = title_elem.find('a')
                    if title_link:
                        title = title_link.get_text(strip=True)
                        url = title_link.get('href', '')
                        
                        # Find snippet
                        snippet_elem = element.find('p')
                        content = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        if title and url:
                            result = SearchResult(
                                source=source_type,
                                title=title,
                                url=url,
                                content=content,
                                relevance_score=0.5
                            )
                            results.append(result)
                            
            except Exception as e:
                logger.warning(f"Failed to parse individual Bing result: {str(e)}")
                continue
        
        return results
    
    def summarize_search_results(self, search_results: Dict[str, List[SearchResult]]) -> Dict[str, str]:
        """
        Summarize search results into a concise format - optimized for speed
        
        Args:
            search_results: Dictionary of search results by category
            
        Returns:
            Dictionary of summarized information by category
        """
        summaries = {}
        
        for category, results in search_results.items():
            if not results:
                if category == 'general':
                    summaries[category] = "General search skipped for faster personalization."
                else:
                    summaries[category] = f"No relevant {category} information found."
                continue
            
            # Quick summary generation for speed
            if category == 'social':
                platforms = set()
                for result in results:
                    if 'github' in result.url.lower():
                        platforms.add('GitHub')
                    elif 'twitter' in result.url.lower():
                        platforms.add('Twitter')
                    elif 'linkedin' in result.url.lower():
                        platforms.add('LinkedIn')
                    elif 'instagram' in result.url.lower():
                        platforms.add('Instagram')
                    elif 'tiktok' in result.url.lower():
                        platforms.add('TikTok')
                    elif 'youtube' in result.url.lower():
                        platforms.add('YouTube')
                
                if platforms:
                    platform_list = ', '.join(sorted(platforms))
                    summaries[category] = f"Found social presence on: {platform_list}. This provides context for personalized recommendations."
                else:
                    summaries[category] = f"Found {len(results)} social media references for personalization context."
            
            elif category == 'location':
                summaries[category] = f"Found {len(results)} local activities and events in your area for relevant suggestions."
            
            elif category == 'activity':
                summaries[category] = f"Found {len(results)} learning resources and guides for your activity interests."
            
            else:
                # Generic summary for any other categories
                summaries[category] = f"Found {len(results)} relevant results for enhanced personalization."
        
        return summaries
    
    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()


# Convenience function for easy integration
def perform_background_search(user_profile: UserProfile) -> Dict[str, Any]:
    """
    Perform background search and return summarized results
    
    Args:
        user_profile: User profile information
        
    Returns:
        Dictionary containing raw results and summaries
    """
    search_service = BackgroundSearchService()
    
    try:
        # Perform the search
        raw_results = search_service.search_user_info(user_profile)
        
        # Summarize the results
        summaries = search_service.summarize_search_results(raw_results)
        
        return {
            'raw_results': raw_results,
            'summaries': summaries,
            'total_results': sum(len(results) for results in raw_results.values())
        }
        
    finally:
        search_service.close()


if __name__ == "__main__":
    # Test the search functionality
    test_profile = UserProfile(
        name="John Doe",
        location="San Francisco, CA",
        social_handles={"github": "johndoe", "twitter": "johndoe"},
        activity="learn python programming"
    )
    
    results = perform_background_search(test_profile)
    print(json.dumps(results['summaries'], indent=2))
