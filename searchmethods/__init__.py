"""
Search methods package for WhatNowAI
Provides background search and web scraping functionality
"""

from .background_search import (
    BackgroundSearchService,
    UserProfile,
    SearchResult,
    perform_background_search
)

from .enhanced_background_search import (
    EnhancedBackgroundSearchService,
    EnhancedUserProfile,
    PersonalizationInsight,
    perform_enhanced_background_search
)

__all__ = [
    'BackgroundSearchService',
    'UserProfile', 
    'SearchResult',
    'perform_background_search',
    'EnhancedBackgroundSearchService',
    'EnhancedUserProfile',
    'PersonalizationInsight',
    'perform_enhanced_background_search'
]