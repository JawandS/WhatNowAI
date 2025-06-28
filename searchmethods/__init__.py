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

__all__ = [
    'BackgroundSearchService',
    'UserProfile', 
    'SearchResult',
    'perform_background_search'
]
