# Search Methods Documentation

## Overview

The `searchmethods` directory contains scripts and utilities for gathering background information about users and their activities through web scraping and online search. This information is used to provide more personalized and contextual responses.

## Components

### 1. Background Search Service (`background_search.py`)

The main service for performing comprehensive background searches on user information.

#### Features:
- **Privacy-focused search**: Uses DuckDuckGo as the primary search engine to respect user privacy
- **Multi-source data gathering**: Searches across general web, social media, location-specific, and activity-related sources
- **Social media profile analysis**: Extracts public information from GitHub, Twitter, LinkedIn
- **Location-based recommendations**: Finds local events and activities
- **Activity-specific guidance**: Searches for tutorials, tips, and resources related to user activities
- **Intelligent result parsing**: Extracts and summarizes relevant information from search results
- **Rate limiting and error handling**: Implements proper delays and fallback mechanisms

#### Data Sources:
1. **General Search**: Web-wide search for user information (excluding major social platforms to avoid duplicates)
2. **Social Media**: Public profiles and posts from:
   - GitHub (using GitHub API for accurate profile data)
   - Twitter (public search results)
   - LinkedIn (public search results)
3. **Location Search**: Local events, activities, and resources in the user's area
4. **Activity Search**: Tutorials, guides, and tips related to the user's desired activity

#### Classes:

##### `UserProfile`
Data structure for user information:
```python
@dataclass
class UserProfile:
    name: str
    location: str = ""
    social_handles: Dict[str, str] = None
    activity: str = ""
```

##### `SearchResult`
Data structure for individual search results:
```python
@dataclass
class SearchResult:
    source: str
    title: str
    url: str
    content: str
    relevance_score: float = 0.0
    timestamp: str = ""
```

##### `BackgroundSearchService`
Main service class with methods:
- `search_user_info()`: Performs comprehensive search across all sources
- `summarize_search_results()`: Creates concise summaries of findings
- `_search_general_info()`: General web search
- `_search_social_media()`: Social platform search
- `_search_location_info()`: Location-specific search
- `_search_activity_info()`: Activity-related search

#### Usage Example:
```python
from searchmethods import UserProfile, perform_background_search

user_profile = UserProfile(
    name="John Doe",
    location="San Francisco, CA",
    social_handles={"github": "johndoe", "twitter": "johndoe"},
    activity="learn python programming"
)

results = perform_background_search(user_profile)
print(results['summaries'])
```

### 2. Integration with Flask App

The background search is integrated into the main Flask application through the `/process` endpoint in `routes.py`.

#### Integration Flow:
1. User submits onboarding information (name, activity, location, social handles)
2. `process_request()` creates a `UserProfile` object
3. `perform_background_search()` is called to gather information
4. Results are summarized and passed to `generate_response_text()`
5. Enhanced response is returned with personalized recommendations

#### API Response Format:
```json
{
  "success": true,
  "result": "Enhanced response text with search insights",
  "name": "User Name",
  "activity": "User Activity",
  "location": {"city": "City", "country": "Country"},
  "social": {"twitter": "@handle", "github": "handle"},
  "search_summaries": {
    "general": "Summary of general findings",
    "social": "Summary of social media findings",
    "location": "Summary of location findings",
    "activity": "Summary of activity findings"
  },
  "total_search_results": 42
}
```

## Configuration

Search behavior is configured in `config/settings.py`:

```python
SEARCH_CONFIG = {
    'MAX_RESULTS_PER_SOURCE': 10,
    'TIMEOUT': 30,
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'SOCIAL_PLATFORMS': ['twitter', 'linkedin', 'instagram', 'facebook', 'github'],
    'MAX_CONCURRENT_REQUESTS': 5
}
```

## Privacy and Ethics

The search methods are designed with privacy and ethics in mind:

1. **Public Data Only**: Only searches for publicly available information
2. **Privacy-focused Search**: Uses DuckDuckGo instead of Google to avoid tracking
3. **Rate Limiting**: Implements delays to be respectful to servers
4. **No Data Storage**: Search results are not permanently stored
5. **User Consent**: Only searches based on information voluntarily provided by users
6. **Transparent Operation**: Users are informed that background research is being performed

## Error Handling

The system includes comprehensive error handling:

- **Network failures**: Graceful fallback when search services are unavailable
- **Rate limiting**: Automatic retries with exponential backoff
- **Invalid data**: Validation and sanitization of input data
- **Service outages**: Fallback to cached or simplified responses
- **Timeout handling**: Prevents hanging requests

## Testing

Use the provided test script to verify functionality:

```bash
python test_search.py
```

This will run a comprehensive test of the background search functionality with sample data.

## Future Enhancements

Potential improvements for the search methods:

1. **Machine Learning Integration**: Use AI to better analyze and categorize search results
2. **Real-time Updates**: Implement caching and periodic updates for frequently searched profiles
3. **Additional Sources**: Integrate with more specialized APIs (Reddit, Stack Overflow, etc.)
4. **Sentiment Analysis**: Analyze the sentiment of social media posts and mentions
5. **Visual Content Analysis**: Process images and videos from social media posts
6. **Trend Analysis**: Identify trending topics related to user activities
7. **Collaborative Filtering**: Recommend activities based on similar user profiles

## Dependencies

Required packages (included in `requirements.txt`):
- `requests`: HTTP requests for web scraping
- `beautifulsoup4`: HTML parsing
- `aiohttp`: Async HTTP requests
- `lxml`: XML/HTML parser
- `urllib3`: HTTP client utilities

## Security Considerations

- All external requests use HTTPS where possible
- User agents are set to standard browser strings to avoid blocking
- No credentials or API keys are exposed in search requests
- Rate limiting prevents being flagged as abusive traffic
- Input sanitization prevents injection attacks
