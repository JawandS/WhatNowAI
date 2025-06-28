#!/usr/bin/env python3
"""
Test script for background search functionality
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from searchmethods.background_search import UserProfile, perform_background_search


def test_background_search():
    """Test the background search functionality"""
    
    print("🔍 Testing Background Search Functionality")
    print("=" * 50)
    
    # Create a test user profile
    test_profile = UserProfile(
        name="John Smith",
        location="San Francisco, CA",
        social_handles={
            "github": "octocat",  # Using a known GitHub user for testing
            "twitter": "github",
            "linkedin": "github"
        },
        activity="learn machine learning"
    )
    
    print(f"👤 Test Profile:")
    print(f"   Name: {test_profile.name}")
    print(f"   Location: {test_profile.location}")
    print(f"   Social Handles: {test_profile.social_handles}")
    print(f"   Activity: {test_profile.activity}")
    print()
    
    print("🚀 Starting background search...")
    
    try:
        # Perform the search
        results = perform_background_search(test_profile)
        
        print("✅ Search completed successfully!")
        print(f"📊 Total results found: {results.get('total_results', 0)}")
        print()
        
        # Display summaries
        print("📋 Search Summaries:")
        print("-" * 30)
        
        summaries = results.get('summaries', {})
        for category, summary in summaries.items():
            print(f"🏷️  {category.upper()}:")
            print(f"   {summary}")
            print()
        
        # Display raw results count by category
        print("📈 Raw Results Breakdown:")
        print("-" * 30)
        
        raw_results = results.get('raw_results', {})
        for category, result_list in raw_results.items():
            print(f"🏷️  {category.upper()}: {len(result_list)} results")
            
            # Show first few results
            for i, result in enumerate(result_list[:2]):
                print(f"     {i+1}. {result.title[:80]}...")
                print(f"        URL: {result.url}")
                print(f"        Content: {result.content[:100]}...")
                print()
        
        print("✨ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during search: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_background_search()
