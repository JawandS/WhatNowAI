#!/usr/bin/env python3
"""
Timing test for the fast search functionality
"""

import sys
import os
import time
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from searchmethods.background_search import UserProfile, perform_background_search


def test_search_timing():
    """Test that search completes within 10 seconds"""
    
    print("⏱️  Fast Search Timing Test")
    print("=" * 40)
    print("Testing that search completes within 10 seconds...")
    print()
    
    # Test with a realistic user profile
    test_profile = UserProfile(
        name="Sarah Johnson",
        location="Seattle, WA",
        social_handles={
            "github": "testuser",
            "linkedin": "sarah-johnson",
            "twitter": "sarahj",
            "instagram": "sarah_photos",
            "youtube": "sarahchannel",
            "tiktok": "sarahtok"
        },
        activity="learn photography"
    )
    
    print(f"👤 Test Profile: {test_profile.name}")
    print(f"📍 Location: {test_profile.location}")
    print(f"🎯 Activity: {test_profile.activity}")
    print(f"📱 Social Platforms: {len([h for h in test_profile.social_handles.values() if h])}")
    print()
    
    # Time the search
    start_time = time.time()
    print("🚀 Starting timed search...")
    
    try:
        results = perform_background_search(test_profile)
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"✅ Search completed!")
        print(f"⏱️  Total time: {elapsed_time:.2f} seconds")
        
        if elapsed_time <= 10:
            print("🎯 SUCCESS: Search completed within 10-second limit!")
        else:
            print("⚠️  WARNING: Search took longer than 10 seconds")
        
        print()
        print(f"📊 Results breakdown:")
        raw_results = results.get('raw_results', {})
        total_results = sum(len(results_list) for results_list in raw_results.values())
        
        for category, results_list in raw_results.items():
            print(f"   {category}: {len(results_list)} results")
        
        print(f"   Total: {total_results} results")
        print()
        
        # Show search focus
        summaries = results.get('summaries', {})
        print("🎯 Search Focus Verification:")
        print(f"   General search: {summaries.get('general', 'No summary')}")
        print(f"   Social media: {summaries.get('social', 'No summary')}")
        
        # Performance metrics
        print()
        print("📈 Performance Metrics:")
        print(f"   ⚡ Speed: {elapsed_time:.2f}s (target: <10s)")
        print(f"   🎯 Focus: Social media + local activities only")
        print(f"   📊 Efficiency: {total_results} relevant results")
        
        return elapsed_time <= 10
        
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"❌ Error after {elapsed_time:.2f}s: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_search_timing()
    if success:
        print("\n🎉 All tests passed! Fast search is working correctly.")
    else:
        print("\n❌ Test failed. Check the search implementation.")
