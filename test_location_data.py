#!/usr/bin/env python3
"""
Simple test to verify location data flow
"""

import requests
import json

def test_location_data_flow():
    """Test the location data flow through the API endpoints"""
    print("🧪 Testing Location Data Flow")
    print("=" * 40)
    
    base_url = "http://127.0.0.1:5002"
    
    # Test 1: Valid coordinates (float)
    print("\n1. Testing valid float coordinates")
    response = requests.post(f"{base_url}/map/events", json={
        "location": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "city": "San Francisco",
            "country": "US"
        },
        "interests": [],
        "activity": "test activity"
    })
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data.get('success')}")
        print(f"   Total events: {data.get('total_events', 0)}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 2: Valid coordinates (string)
    print("\n2. Testing valid string coordinates")
    response = requests.post(f"{base_url}/map/events", json={
        "location": {
            "latitude": "37.7749",
            "longitude": "-122.4194",
            "city": "San Francisco",
            "country": "US"
        },
        "interests": [],
        "activity": "test activity"
    })
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data.get('success')}")
        print(f"   Total events: {data.get('total_events', 0)}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 3: Empty location data (should trigger our fallback)
    print("\n3. Testing empty location data")
    response = requests.post(f"{base_url}/map/events", json={
        "location": {},
        "interests": [],
        "activity": "test activity"
    })
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        data = response.json()
        print(f"   Expected error: {data.get('message')}")
    else:
        print(f"   Unexpected response: {response.text}")
    
    # Test 4: Invalid coordinates
    print("\n4. Testing invalid coordinates")
    response = requests.post(f"{base_url}/map/events", json={
        "location": {
            "latitude": "invalid",
            "longitude": "coordinates",
            "city": "Test",
            "country": "US"
        },
        "interests": [],
        "activity": "test activity"
    })
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        data = response.json()
        print(f"   Expected error: {data.get('message')}")
    else:
        print(f"   Unexpected response: {response.text}")

if __name__ == "__main__":
    try:
        test_location_data_flow()
        print("\n✅ Location data flow test completed!")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app. Make sure it's running on port 5002.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
