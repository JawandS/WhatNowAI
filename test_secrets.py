#!/usr/bin/env python3
"""
Test script to verify API keys are being loaded correctly from secrets.txt
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import (
    TICKETMASTER_API_KEY, 
    OPENAI_API_KEY, 
    check_api_keys,
    _secrets
)

def test_secrets_loading():
    """Test that secrets are being loaded correctly"""
    print("🧪 Testing Secrets Loading")
    print("=" * 40)
    
    print(f"Raw secrets loaded: {list(_secrets.keys())}")
    print(f"Secrets content (safe): {[(k, v[:10] + '...' if len(v) > 10 else v) for k, v in _secrets.items()]}")
    
    print(f"\nTicketmaster API Key: {'SET' if TICKETMASTER_API_KEY else 'NOT SET'}")
    if TICKETMASTER_API_KEY:
        print(f"Key preview: {TICKETMASTER_API_KEY[:10]}...")
        print(f"Key length: {len(TICKETMASTER_API_KEY)}")
    
    print(f"\nOpenAI API Key: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
    if OPENAI_API_KEY:
        print(f"Key preview: {OPENAI_API_KEY[:10]}...")
        print(f"Key length: {len(OPENAI_API_KEY)}")
    
    print("\n" + "=" * 40)
    check_api_keys()

if __name__ == "__main__":
    test_secrets_loading()
