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
        Search for information about the user across multiple sources
        
        Args:
            user_profile: User profile containing name, location, social handles, etc.
            
        Returns:
            Dictionary of search results organized by source
        """
        logger.info(f"Starting background search for user: {user_profile.name}")
        
        results = {
            'general': [],
            'social': [],
            'location': [],
            'activity': []
        }
        
        if not self.session:
            self.session = self._setup_session()
        
        try:
            # Search for general information about the user
            if user_profile.name:
                general_results = self._search_general_info(user_profile.name)
                results['general'].extend(general_results)
            
            # Search social media platforms
            if user_profile.social_handles:
                social_results = self._search_social_media(user_profile.social_handles)
                results['social'].extend(social_results)
            
            # Search location-specific information
            if user_profile.location:
                location_results = self._search_location_info(user_profile.location, user_profile.activity)
                results['location'].extend(location_results)
            
            # Search activity-related information
            if user_profile.activity:
                activity_results = self._search_activity_info(user_profile.activity, user_profile.location)
                results['activity'].extend(activity_results)
                
        except Exception as e:
            logger.error(f"Error during background search: {str(e)}")
        
        return results
    
    def _search_general_info(self, name: str) -> List[SearchResult]:
        """Search for general information about a person"""
        results = []
        
        # Use DuckDuckGo for privacy-focused search
        query = quote_plus(f'"{name}" -site:facebook.com -site:twitter.com')
        search_urls = [
            f"https://duckduckgo.com/html/?q={query}",
            f"https://www.bing.com/search?q={query}",
        ]
        
        for url in search_urls:
            try:
                response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
                if response.status_code == 200:
                    search_results = self._parse_search_results(response.text, 'general')
                    results.extend(search_results[:self.config.get('MAX_RESULTS_PER_SOURCE', 10)])
                    time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.warning(f"Failed to search {url}: {str(e)}")
                continue
        
        return results
    
    def _search_social_media(self, social_handles: Dict[str, str]) -> List[SearchResult]:
        """Search social media platforms for user information"""
        results = []
        
        for platform, handle in social_handles.items():
            if not handle:
                continue
                
            try:
                if platform.lower() == 'twitter':
                    # Search for Twitter profile information
                    results.extend(self._search_twitter_info(handle))
                elif platform.lower() == 'linkedin':
                    # Search for LinkedIn profile information
                    results.extend(self._search_linkedin_info(handle))
                elif platform.lower() == 'github':
                    # Search for GitHub profile information
                    results.extend(self._search_github_info(handle))
                    
            except Exception as e:
                logger.warning(f"Failed to search {platform} for {handle}: {str(e)}")
                continue
        
        return results
    
    def _search_location_info(self, location: str, activity: str = "") -> List[SearchResult]:
        """Search for location-specific information and events"""
        results = []
        
        # Search for events and activities in the location
        queries = [
            f"events {location} today",
            f"things to do {location}",
            f"local activities {location}",
        ]
        
        if activity:
            queries.append(f"{activity} {location}")
            queries.append(f"{activity} events {location}")
        
        for query in queries:
            try:
                encoded_query = quote_plus(query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
                if response.status_code == 200:
                    search_results = self._parse_search_results(response.text, 'location')
                    results.extend(search_results[:5])
                    time.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Failed to search location info for {query}: {str(e)}")
                continue
        
        return results
    
    def _search_activity_info(self, activity: str, location: str = "") -> List[SearchResult]:
        """Search for activity-related information and recommendations"""
        results = []
        
        queries = [
            f"how to {activity}",
            f"{activity} tips recommendations",
            f"best {activity} guide",
        ]
        
        if location:
            queries.append(f"{activity} in {location}")
            queries.append(f"where to {activity} {location}")
        
        for query in queries:
            try:
                encoded_query = quote_plus(query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=self.config.get('TIMEOUT', 30))
                if response.status_code == 200:
                    search_results = self._parse_search_results(response.text, 'activity')
                    results.extend(search_results[:5])
                    time.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Failed to search activity info for {query}: {str(e)}")
                continue
        
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
        Summarize search results into a concise format
        
        Args:
            search_results: Dictionary of search results by category
            
        Returns:
            Dictionary of summarized information by category
        """
        summaries = {}
        
        for category, results in search_results.items():
            if not results:
                summaries[category] = f"No relevant {category} information found."
                continue
            
            # Extract key information from results
            key_points = []
            
            for result in results[:5]:  # Limit to top 5 results per category
                if result.content:
                    # Extract key sentences or phrases
                    sentences = result.content.split('.')
                    for sentence in sentences[:2]:  # Take first 2 sentences
                        sentence = sentence.strip()
                        if len(sentence) > 20:  # Filter out very short sentences
                            key_points.append(sentence)
            
            # Create summary
            if key_points:
                summary = f"Found {len(results)} {category} results. Key insights: " + \
                         ". ".join(key_points[:3]) + "."
            else:
                summary = f"Found {len(results)} {category} results but limited detailed information available."
            
            summaries[category] = summary
        
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
