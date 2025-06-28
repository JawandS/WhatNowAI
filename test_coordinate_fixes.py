#!/usr/bin/env python3
"""
Test script to verify coordinate validation and conversion fixes
"""

import sys
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.helpers import validate_coordinates


def test_coordinate_validation():
    """Test coordinate validation with various inputs"""
    print("🔍 Testing Coordinate Validation")
    print("=" * 40)
    
    test_cases = [
        # (latitude, longitude, expected_result, description)
        (37.7749, -122.4194, True, "Valid SF coordinates (float)"),
        ("37.7749", "-122.4194", True, "Valid SF coordinates (string)"),
        (None, None, False, "None values"),
        ("invalid", "also_invalid", False, "Invalid strings"),
        (91, 0, False, "Latitude out of range (>90)"),
        (-91, 0, False, "Latitude out of range (<-90)"),
        (0, 181, False, "Longitude out of range (>180)"),
        (0, -181, False, "Longitude out of range (<-180)"),
        (0, 0, True, "Zero coordinates"),
        ("", "", False, "Empty strings"),
        (float('inf'), 0, False, "Infinity value"),
        (float('nan'), 0, False, "NaN value"),
    ]
    
    for lat, lon, expected, description in test_cases:
        try:
            result = validate_coordinates(lat, lon)
            status = "✅" if result == expected else "❌"
            print(f"{status} {description}: {lat}, {lon} -> {result}")
            if result != expected:
                print(f"   Expected: {expected}, Got: {result}")
        except Exception as e:
            print(f"❌ {description}: Exception - {e}")


def test_coordinate_conversion_in_route():
    """Test the coordinate conversion logic that we added to routes"""
    print("\n🔄 Testing Coordinate Conversion Logic")
    print("=" * 40)
    
    def convert_coordinates(latitude, longitude):
        """Simulate the conversion logic from routes.py"""
        try:
            if latitude is not None:
                latitude = float(latitude)
            if longitude is not None:
                longitude = float(longitude)
            return latitude, longitude, None
        except (ValueError, TypeError) as e:
            return None, None, str(e)
    
    test_cases = [
        # (latitude, longitude, description)
        ("37.7749", "-122.4194", "String coordinates"),
        (37.7749, -122.4194, "Float coordinates"),
        ("invalid", "123", "Mixed invalid/valid"),
        (None, None, "None values"),
        ("", "", "Empty strings"),
    ]
    
    for lat, lon, description in test_cases:
        converted_lat, converted_lon, error = convert_coordinates(lat, lon)
        if error:
            print(f"❌ {description}: Error - {error}")
        else:
            valid = validate_coordinates(converted_lat, converted_lon)
            status = "✅" if valid else "⚠️"
            print(f"{status} {description}: {lat}, {lon} -> {converted_lat}, {converted_lon} (Valid: {valid})")


def test_json_payload_simulation():
    """Simulate the JSON payload handling"""
    print("\n📡 Testing JSON Payload Simulation")
    print("=" * 40)
    
    # Simulate different types of JSON payloads that might be sent to the API
    test_payloads = [
        {
            "location": {
                "latitude": 37.7749,
                "longitude": -122.4194
            },
            "description": "Numeric coordinates"
        },
        {
            "location": {
                "latitude": "37.7749",
                "longitude": "-122.4194"
            },
            "description": "String coordinates"
        },
        {
            "location": {
                "latitude": "invalid",
                "longitude": "coordinates"
            },
            "description": "Invalid string coordinates"
        },
        {
            "location": {},
            "description": "Missing coordinates"
        }
    ]
    
    for payload in test_payloads:
        location_data = payload.get('location', {})
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        
        print(f"\n📦 {payload['description']}")
        print(f"   Raw: lat={latitude} ({type(latitude)}), lon={longitude} ({type(longitude)})")
        
        # Apply our conversion logic
        try:
            if latitude is not None:
                latitude = float(latitude)
            if longitude is not None:
                longitude = float(longitude)
            
            valid = validate_coordinates(latitude, longitude)
            status = "✅" if valid else "❌"
            print(f"   {status} Converted: lat={latitude}, lon={longitude} (Valid: {valid})")
            
        except (ValueError, TypeError) as e:
            print(f"   ❌ Conversion failed: {e}")


if __name__ == "__main__":
    test_coordinate_validation()
    test_coordinate_conversion_in_route()
    test_json_payload_simulation()
    
    print("\n🎉 Coordinate testing completed!")
    print("💡 The fixes should handle string coordinates and invalid inputs properly.")
