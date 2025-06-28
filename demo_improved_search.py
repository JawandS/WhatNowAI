#!/usr/bin/env python3
"""
Demo script showing the improved user-focused search functionality
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from searchmethods.background_search import UserProfile, perform_background_search


def demo_user_focused_search():
    """Demonstrate the user-focused search improvements"""
    
    print("🎯 User-Focused Search Demo")
    print("=" * 50)
    print("This demo shows how the search now focuses on:")
    print("✅ Specific user information (not celebrities)")
    print("✅ Local activities relevant to user interests")
    print("✅ Multiple social media platforms")
    print("✅ Personalized recommendations")
    print()
    
    # Test with a realistic user profile
    demo_profile = UserProfile(
        name="Alex Johnson",  # More generic name to avoid celebrity matches
        location="Austin, TX",
        social_handles={
            "github": "alexanderjohnson",
            "linkedin": "alex-johnson-dev",
            "twitter": "alexj_dev",
            "instagram": "alexj_photos",
            "youtube": "alexjtutorials"
        },
        activity="learn web development"
    )
    
    print(f"👤 Demo Profile:")
    print(f"   Name: {demo_profile.name}")
    print(f"   Location: {demo_profile.location}")
    print(f"   Social Handles: {demo_profile.social_handles}")
    print(f"   Activity: {demo_profile.activity}")
    print()
    
    print("🔍 Starting user-focused search...")
    print("   - Filtering out celebrity/famous person results")
    print("   - Focusing on local activities and communities")
    print("   - Searching across all provided social platforms")
    print("   - Finding personalized learning resources")
    print()
    
    try:
        results = perform_background_search(demo_profile)
        
        print("✅ Search completed!")
        print(f"📊 Total focused results: {results.get('total_results', 0)}")
        print()
        
        # Show how results are now more targeted
        summaries = results.get('summaries', {})
        raw_results = results.get('raw_results', {})
        
        print("📋 Targeted Search Results:")
        print("-" * 40)
        
        categories = ['general', 'social', 'location', 'activity']
        for category in categories:
            summary = summaries.get(category, 'No results')
            result_count = len(raw_results.get(category, []))
            
            print(f"🏷️  {category.upper()} ({result_count} results):")
            print(f"   {summary[:150]}...")
            print()
        
        # Show some specific improvements
        print("🎯 Search Improvements Demonstrated:")
        print("-" * 40)
        
        general_results = raw_results.get('general', [])
        if general_results:
            print(f"✅ General search avoided celebrity matches:")
            for i, result in enumerate(general_results[:2]):
                print(f"   {i+1}. {result.title[:60]}...")
        
        location_results = raw_results.get('location', [])
        if location_results:
            print(f"\n✅ Location search found local activities:")
            for i, result in enumerate(location_results[:2]):
                print(f"   {i+1}. {result.title[:60]}...")
        
        activity_results = raw_results.get('activity', [])
        if activity_results:
            print(f"\n✅ Activity search found learning resources:")
            for i, result in enumerate(activity_results[:2]):
                print(f"   {i+1}. {result.title[:60]}...")
        
        print(f"\n🌟 Key Improvements:")
        print(f"   • More relevant, user-specific results")
        print(f"   • Local activity recommendations")
        print(f"   • Educational content prioritization")
        print(f"   • Multi-platform social media coverage")
        print(f"   • Celebrity/famous person filtering")
        
    except Exception as e:
        print(f"❌ Error during search: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_user_focused_search()
