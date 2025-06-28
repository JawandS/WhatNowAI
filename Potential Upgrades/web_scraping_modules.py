# searchmethods/scrapers/web_scrapers.py
"""
Advanced web scraping modules for various platforms
"""
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import re
import json
from urllib.parse import quote_plus, urljoin
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import cloudscraper
from fake_useragent import UserAgent
from datetime import datetime
import time

from ..core import BaseSearchModule, SearchResult, DataSource

logger = logging.getLogger(__name__)


class WebScraperBase(BaseSearchModule):
    """Base class for web scrapers"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.ua = UserAgent()
        self.session = None
        self.use_selenium = config.get('use_selenium', False)
        self.driver = None
        
    async def _get_session(self):
        """Get aiohttp session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers={'User-Agent': self.ua.random},
                timeout=timeout
            )
        return self.session
    
    def _get_selenium_driver(self):
        """Get Selenium driver for JavaScript-heavy sites"""
        if not self.driver and self.use_selenium:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'user-agent={self.ua.random}')
            
            try:
                self.driver = webdriver.Chrome(options=options)
            except Exception as e:
                logger.error(f"Failed to create Selenium driver: {e}")
                self.use_selenium = False
        
        return self.driver
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content"""
        try:
            if self.use_selenium:
                driver = self._get_selenium_driver()
                if driver:
                    driver.get(url)
                    time.sleep(2)  # Wait for JS to load
                    return driver.page_source
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                    
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            
        return None
    
    def _extract_text(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract text using CSS selectors"""
        texts = []
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text:
                    texts.append(text)
        return ' '.join(texts)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()


class GoogleSearchScraper(WebScraperBase):
    """Enhanced Google search scraper"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.WEB_SEARCH
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Google and parse results"""
        results = []
        num_pages = kwargs.get('num_pages', 3)
        
        for page in range(num_pages):
            url = self._build_search_url(query, page)
            html = await self._fetch_page(url)
            
            if html:
                page_results = self._parse_results(html, query)
                results.extend(page_results)
                
                # Rate limiting between pages
                await asyncio.sleep(2)
        
        return results
    
    def _build_search_url(self, query: str, page: int) -> str:
        """Build Google search URL"""
        start = page * 10
        return f"https://www.google.com/search?q={quote_plus(query)}&start={start}"
    
    def _parse_results(self, html: str, query: str) -> List[SearchResult]:
        """Parse Google search results"""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result divs
        result_divs = soup.find_all('div', class_='g')
        
        for div in result_divs:
            try:
                # Extract title and URL
                title_elem = div.find('h3')
                link_elem = div.find('a', href=True)
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = link_elem['href']
                
                # Extract snippet
                snippet_elem = div.find('span', class_='aCOpRe') or div.find('div', class_='IsZvec')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # Calculate relevance
                relevance = self._calculate_relevance(title, snippet, query)
                
                result = SearchResult(
                    source=self.get_source_type(),
                    title=title,
                    url=url,
                    content=snippet,
                    relevance_score=relevance,
                    metadata={'search_query': query}
                )
                
                results.append(result)
                
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        return results
    
    def _calculate_relevance(self, title: str, content: str, query: str) -> float:
        """Calculate relevance score"""
        text = f"{title} {content}".lower()
        query_terms = query.lower().split()
        
        matches = sum(1 for term in query_terms if term in text)
        relevance = matches / len(query_terms) if query_terms else 0
        
        # Boost for exact phrase match
        if query.lower() in text:
            relevance = min(relevance + 0.3, 1.0)
        
        return relevance


class LinkedInScraper(WebScraperBase):
    """LinkedIn profile scraper"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.PROFESSIONAL
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search LinkedIn profiles"""
        results = []
        
        # LinkedIn search URL
        search_url = f"https://www.google.com/search?q=site:linkedin.com/in+{quote_plus(query)}"
        
        # Use Google to find LinkedIn profiles
        html = await self._fetch_page(search_url)
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract LinkedIn URLs from Google results
            linkedin_urls = self._extract_linkedin_urls(soup)
            
            # Scrape each profile
            for url in linkedin_urls[:5]:  # Limit to 5 profiles
                profile_data = await self._scrape_profile(url)
                if profile_data:
                    results.append(profile_data)
                await asyncio.sleep(2)  # Rate limiting
        
        return results
    
    def _extract_linkedin_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract LinkedIn profile URLs from Google results"""
        urls = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'linkedin.com/in/' in href:
                # Clean URL
                if href.startswith('/url?q='):
                    href = href.split('/url?q=')[1].split('&')[0]
                urls.append(href)
        
        return list(set(urls))  # Remove duplicates
    
    async def _scrape_profile(self, url: str) -> Optional[SearchResult]:
        """Scrape LinkedIn profile page"""
        try:
            # Note: Full LinkedIn scraping requires authentication
            # This is a simplified version for public data
            
            html = await self._fetch_page(url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract basic info from page
            title = soup.find('title')
            title_text = title.get_text() if title else "LinkedIn Profile"
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ""
            
            # Extract any visible text
            content = self._extract_text(soup, [
                'h1', 'h2', 'h3', 'p', 
                '.pv-top-card__summary',
                '.pv-about__summary-text'
            ])
            
            return SearchResult(
                source=self.get_source_type(),
                title=title_text,
                url=url,
                content=f"{description} {content}"[:500],
                relevance_score=0.8,
                metadata={'platform': 'linkedin'}
            )
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile {url}: {e}")
            return None


class TwitterScraper(WebScraperBase):
    """Twitter/X scraper using multiple methods"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.SOCIAL_MEDIA
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Twitter/X"""
        results = []
        
        # Method 1: Use nitter instances (Twitter frontend)
        nitter_results = await self._search_nitter(query)
        results.extend(nitter_results)
        
        # Method 2: Google search for Twitter
        google_results = await self._search_via_google(query)
        results.extend(google_results)
        
        return results
    
    async def _search_nitter(self, query: str) -> List[SearchResult]:
        """Search using Nitter instances"""
        results = []
        
        # List of public Nitter instances
        nitter_instances = [
            'nitter.net',
            'nitter.42l.fr',
            'nitter.pussthecat.org'
        ]
        
        for instance in nitter_instances:
            try:
                url = f"https://{instance}/search?q={quote_plus(query)}&f=users"
                html = await self._fetch_page(url)
                
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse user results
                    for user_card in soup.find_all('div', class_='timeline-item'):
                        result = self._parse_nitter_user(user_card, query)
                        if result:
                            results.append(result)
                    
                    if results:
                        break  # Use first working instance
                        
            except Exception as e:
                logger.debug(f"Nitter instance {instance} failed: {e}")
                continue
        
        return results
    
    def _parse_nitter_user(self, user_card, query: str) -> Optional[SearchResult]:
        """Parse Nitter user card"""
        try:
            username = user_card.find('a', class_='username')
            fullname = user_card.find('a', class_='fullname')
            bio = user_card.find('div', class_='tweet-content')
            
            if not username:
                return None
            
            username_text = username.get_text(strip=True)
            fullname_text = fullname.get_text(strip=True) if fullname else ""
            bio_text = bio.get_text(strip=True) if bio else ""
            
            url = f"https://twitter.com/{username_text.replace('@', '')}"
            
            return SearchResult(
                source=self.get_source_type(),
                title=f"{fullname_text} (@{username_text})",
                url=url,
                content=bio_text,
                relevance_score=0.7,
                metadata={
                    'platform': 'twitter',
                    'username': username_text,
                    'search_query': query
                }
            )
            
        except Exception as e:
            logger.debug(f"Error parsing Nitter user: {e}")
            return None
    
    async def _search_via_google(self, query: str) -> List[SearchResult]:
        """Search Twitter via Google"""
        results = []
        
        search_query = f"site:twitter.com {query}"
        url = f"https://www.google.com/search?q={quote_plus(search_query)}"
        
        html = await self._fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            for result_div in soup.find_all('div', class_='g'):
                try:
                    link = result_div.find('a', href=True)
                    title = result_div.find('h3')
                    snippet = result_div.find('span', class_='aCOpRe')
                    
                    if link and 'twitter.com' in link['href']:
                        results.append(SearchResult(
                            source=self.get_source_type(),
                            title=title.get_text() if title else "Twitter Result",
                            url=link['href'],
                            content=snippet.get_text() if snippet else "",
                            relevance_score=0.6,
                            metadata={'platform': 'twitter', 'via': 'google'}
                        ))
                        
                except Exception as e:
                    logger.debug(f"Error parsing Google Twitter result: {e}")
                    continue
        
        return results


class InstagramScraper(WebScraperBase):
    """Instagram scraper"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.SOCIAL_MEDIA
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Instagram profiles"""
        results = []
        
        # Method 1: Search via Google
        google_results = await self._search_via_google(query)
        results.extend(google_results)
        
        # Method 2: Use alternative viewers
        viewer_results = await self._search_via_viewers(query)
        results.extend(viewer_results)
        
        return results
    
    async def _search_via_google(self, query: str) -> List[SearchResult]:
        """Search Instagram via Google"""
        results = []
        
        search_query = f"site:instagram.com {query}"
        url = f"https://www.google.com/search?q={quote_plus(search_query)}"
        
        html = await self._fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            for result_div in soup.find_all('div', class_='g'):
                try:
                    link = result_div.find('a', href=True)
                    title = result_div.find('h3')
                    snippet = result_div.find('span', class_='aCOpRe')
                    
                    if link and 'instagram.com' in link['href']:
                        results.append(SearchResult(
                            source=self.get_source_type(),
                            title=title.get_text() if title else "Instagram Profile",
                            url=link['href'],
                            content=snippet.get_text() if snippet else "",
                            relevance_score=0.6,
                            metadata={'platform': 'instagram', 'via': 'google'}
                        ))
                        
                except Exception as e:
                    logger.debug(f"Error parsing Google Instagram result: {e}")
                    continue
        
        return results
    
    async def _search_via_viewers(self, query: str) -> List[SearchResult]:
        """Search using Instagram viewers"""
        results = []
        
        # List of Instagram viewer sites
        viewers = [
            'picuki.com',
            'imginn.com'
        ]
        
        for viewer in viewers:
            try:
                url = f"https://{viewer}/search/{quote_plus(query)}"
                html = await self._fetch_page(url)
                
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse based on viewer structure
                    if 'picuki' in viewer:
                        results.extend(self._parse_picuki_results(soup, query))
                    elif 'imginn' in viewer:
                        results.extend(self._parse_imginn_results(soup, query))
                    
                    if results:
                        break
                        
            except Exception as e:
                logger.debug(f"Instagram viewer {viewer} failed: {e}")
                continue
        
        return results
    
    def _parse_picuki_results(self, soup: BeautifulSoup, query: str) -> List[SearchResult]:
        """Parse Picuki search results"""
        results = []
        
        for profile in soup.find_all('div', class_='profile-result'):
            try:
                username = profile.find('a', class_='username')
                fullname = profile.find('div', class_='fullname')
                bio = profile.find('div', class_='bio')
                
                if username:
                    username_text = username.get_text(strip=True)
                    url = f"https://instagram.com/{username_text}"
                    
                    results.append(SearchResult(
                        source=self.get_source_type(),
                        title=f"{fullname.get_text(strip=True) if fullname else username_text}",
                        url=url,
                        content=bio.get_text(strip=True) if bio else "",
                        relevance_score=0.7,
                        metadata={
                            'platform': 'instagram',
                            'username': username_text,
                            'via': 'picuki'
                        }
                    ))
                    
            except Exception as e:
                logger.debug(f"Error parsing Picuki result: {e}")
                continue
        
        return results
    
    def _parse_imginn_results(self, soup: BeautifulSoup, query: str) -> List[SearchResult]:
        """Parse Imginn search results"""
        # Similar implementation for imginn
        return []


class GitHubScraper(WebScraperBase):
    """GitHub profile and repository scraper"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.PROFESSIONAL
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search GitHub users and repositories"""
        results = []
        
        # Search users
        user_results = await self._search_users(query)
        results.extend(user_results)
        
        # Search repositories
        repo_results = await self._search_repositories(query)
        results.extend(repo_results)
        
        return results
    
    async def _search_users(self, query: str) -> List[SearchResult]:
        """Search GitHub users via API"""
        results = []
        
        try:
            url = f"https://api.github.com/search/users?q={quote_plus(query)}"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for user in data.get('items', [])[:5]:
                        # Fetch user details
                        user_data = await self._fetch_user_details(user['login'])
                        if user_data:
                            results.append(user_data)
                            
        except Exception as e:
            logger.error(f"Error searching GitHub users: {e}")
        
        return results
    
    async def _fetch_user_details(self, username: str) -> Optional[SearchResult]:
        """Fetch detailed user information"""
        try:
            url = f"https://api.github.com/users/{username}"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    content = []
                    if data.get('bio'):
                        content.append(f"Bio: {data['bio']}")
                    if data.get('company'):
                        content.append(f"Company: {data['company']}")
                    if data.get('location'):
                        content.append(f"Location: {data['location']}")
                    if data.get('blog'):
                        content.append(f"Website: {data['blog']}")
                    
                    content.append(f"Public repos: {data.get('public_repos', 0)}")
                    content.append(f"Followers: {data.get('followers', 0)}")
                    
                    return SearchResult(
                        source=self.get_source_type(),
                        title=f"{data.get('name', username)} (@{username})",
                        url=data['html_url'],
                        content=' | '.join(content),
                        relevance_score=0.8,
                        metadata={
                            'platform': 'github',
                            'username': username,
                            'type': 'user'
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Error fetching GitHub user {username}: {e}")
            
        return None
    
    async def _search_repositories(self, query: str) -> List[SearchResult]:
        """Search GitHub repositories"""
        results = []
        
        try:
            url = f"https://api.github.com/search/repositories?q={quote_plus(query)}"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for repo in data.get('items', [])[:3]:
                        results.append(SearchResult(
                            source=self.get_source_type(),
                            title=f"{repo['full_name']} - {repo.get('description', 'No description')[:100]}",
                            url=repo['html_url'],
                            content=f"Stars: {repo['stargazers_count']} | Forks: {repo['forks_count']} | Language: {repo.get('language', 'Unknown')}",
                            relevance_score=0.6,
                            metadata={
                                'platform': 'github',
                                'type': 'repository',
                                'owner': repo['owner']['login']
                            }
                        ))
                        
        except Exception as e:
            logger.error(f"Error searching GitHub repositories: {e}")
        
        return results


class RedditScraper(WebScraperBase):
    """Reddit posts and comments scraper"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.FORUMS
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search Reddit posts and comments"""
        results = []
        
        # Use Reddit's JSON API (no auth required for public data)
        search_url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&limit=10"
        
        try:
            session = await self._get_session()
            async with session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for post in data['data']['children']:
                        post_data = post['data']
                        
                        # Create result
                        result = SearchResult(
                            source=self.get_source_type(),
                            title=post_data['title'],
                            url=f"https://reddit.com{post_data['permalink']}",
                            content=post_data.get('selftext', '')[:500],
                            relevance_score=self._calculate_reddit_relevance(post_data, query),
                            metadata={
                                'platform': 'reddit',
                                'subreddit': post_data['subreddit'],
                                'author': post_data['author'],
                                'score': post_data['score'],
                                'num_comments': post_data['num_comments']
                            }
                        )
                        
                        results.append(result)
                        
        except Exception as e:
            logger.error(f"Error searching Reddit: {e}")
        
        return results
    
    def _calculate_reddit_relevance(self, post_data: dict, query: str) -> float:
        """Calculate relevance based on Reddit metrics"""
        base_relevance = 0.5
        
        # Boost for query match in title
        if query.lower() in post_data['title'].lower():
            base_relevance += 0.2
        
        # Boost for high engagement
        if post_data['score'] > 100:
            base_relevance += 0.1
        if post_data['num_comments'] > 50:
            base_relevance += 0.1
        
        # Boost for recent posts
        import time
        post_age_days = (time.time() - post_data['created_utc']) / 86400
        if post_age_days < 30:
            base_relevance += 0.1
        
        return min(base_relevance, 1.0)


class NewsArchiveScraper(WebScraperBase):
    """Scraper for news archives and articles"""
    
    def get_source_type(self) -> DataSource:
        return DataSource.NEWS_ARTICLES
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search news archives"""
        results = []
        
        # Search multiple news sources
        sources = [
            ('Google News', self._search_google_news),
            ('Archive.org', self._search_archive_org),
        ]
        
        for source_name, search_func in sources:
            try:
                source_results = await search_func(query)
                results.extend(source_results)
            except Exception as e:
                logger.error(f"Error searching {source_name}: {e}")
        
        return results
    
    async def _search_google_news(self, query: str) -> List[SearchResult]:
        """Search Google News"""
        results = []
        
        url = f"https://news.google.com/search?q={quote_plus(query)}"
        html = await self._fetch_page(url)
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse news articles
            for article in soup.find_all('article'):
                try:
                    title_elem = article.find('h3') or article.find('h4')
                    link_elem = article.find('a', href=True)
                    time_elem = article.find('time')
                    
                    if title_elem and link_elem:
                        # Google News links are encoded
                        url = link_elem['href']
                        if url.startswith('./'):
                            url = f"https://news.google.com{url[1:]}"
                        
                        results.append(SearchResult(
                            source=self.get_source_type(),
                            title=title_elem.get_text(strip=True),
                            url=url,
                            content=f"Published: {time_elem.get_text() if time_elem else 'Unknown'}",
                            relevance_score=0.7,
                            metadata={
                                'source': 'google_news',
                                'type': 'news_article'
                            }
                        ))
                        
                except Exception as e:
                    logger.debug(f"Error parsing news article: {e}")
                    continue
        
        return results[:5]  # Limit results
    
    async def _search_archive_org(self, query: str) -> List[SearchResult]:
        """Search Internet Archive"""
        results = []
        
        # Use Archive.org search API
        url = f"https://archive.org/advancedsearch.php?q={quote_plus(query)}&output=json&rows=5"
        
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for doc in data.get('response', {}).get('docs', []):
                        results.append(SearchResult(
                            source=self.get_source_type(),
                            title=doc.get('title', 'Archived Document'),
                            url=f"https://archive.org/details/{doc.get('identifier', '')}",
                            content=doc.get('description', '')[:300],
                            relevance_score=0.6,
                            metadata={
                                'source': 'archive.org',
                                'date': doc.get('publicdate', ''),
                                'type': doc.get('mediatype', 'unknown')
                            }
                        ))
                        
        except Exception as e:
            logger.error(f"Error searching Archive.org: {e}")
        
        return results
