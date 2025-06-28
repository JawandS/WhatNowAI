from flask import Flask, render_template, request, jsonify, abort

app = Flask(__name__)

@app.route('/')
def home():
    """Render the homepage with the form"""
    return render_template('home.html')

@app.route('/submit', methods=['POST'])
def submit_info():
    """Handle form submission with user's name and activity"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        activity = data.get('activity', '').strip()
        
        if not name or not activity:
            return jsonify({
                'success': False,
                'message': 'Please provide both your name and what you want to do.'
            }), 400
        
        # Process the user input - start background processing
        response_message = f"Hello {name}! I'm processing your request to {activity}. Please wait while I work on this..."
        
        return jsonify({
            'success': True,
            'message': response_message,
            'name': name,
            'activity': activity,
            'processing': True
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Please provide a message.'
            }), 400
        
        # Simple response logic (you can enhance this with AI)
        response = f"I received your message: '{message}'. How can I help you further?"
        
        return jsonify({
            'success': True,
            'response': response
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your message.'
        }), 500

@app.route('/process', methods=['POST'])
def process_request():
    """Handle background processing of user request"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        activity = data.get('activity', '').strip()
        location_data = data.get('location', {})
        
        if not name or not activity:
            return jsonify({
                'success': False,
                'message': 'Missing name or activity information.'
            }), 400
        
        # Extract location information
        country = location_data.get('country', 'Unknown')
        zipcode = location_data.get('zipcode', 'Unknown')
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        city = location_data.get('city', 'Unknown')
        
        # TODO: Add your actual AI/processing logic here
        # This is a placeholder for now - simulate processing time
        import time
        time.sleep(3)  # Simulate processing delay
        
        # Placeholder response - replace with actual AI logic
        # Now includes location-aware suggestions with coordinates
        location_str = f"{city}, {country}"
        if zipcode != 'Unknown':
            location_str += f" ({zipcode})"
        
        result = f"Great news, {name}! I've analyzed your request to {activity} in {location_str}.\n\n" \
                f"Here are some location-specific suggestions:\n\n" \
                f"1. Start by breaking down '{activity}' into smaller steps\n" \
                f"2. Research local resources in {country} that can help with {activity}\n" \
                f"3. Check for any location-specific requirements or regulations\n" \
                f"4. Set a timeline for completion\n" \
                f"5. Connect with local communities or groups in your area\n\n"
        
        if latitude and longitude:
            result += f"Based on your precise location ({latitude:.4f}, {longitude:.4f}), I can provide even more targeted recommendations.\n\n"
        
        result += f"Would you like me to help you create a detailed plan specific to your location?"
        
        return jsonify({
            'success': True,
            'result': result,
            'name': name,
            'activity': activity,
            'location': location_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500

@app.route('/geocode', methods=['POST'])
def reverse_geocode():
    """Reverse geocode latitude/longitude to get address information"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return jsonify({
                'success': False,
                'message': 'Missing latitude or longitude.'
            }), 400
        
        # Using Nominatim (OpenStreetMap) for free reverse geocoding
        import requests
        
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'format': 'json',
            'lat': latitude,
            'lon': longitude,
            'zoom': 18,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'WhatNowAI/1.0'  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            geo_data = response.json()
            address = geo_data.get('address', {})
            
            # Extract relevant information
            country = address.get('country', 'Unknown')
            city = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet', 'Unknown')
            zipcode = address.get('postcode', 'Unknown')
            
            return jsonify({
                'success': True,
                'location': {
                    'country': country,
                    'city': city,
                    'zipcode': zipcode,
                    'latitude': latitude,
                    'longitude': longitude,
                    'full_address': geo_data.get('display_name', 'Unknown')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to geocode location.'
            }), 500
            
    except Exception as e:
        print(f"Geocoding error: {e}")  # For debugging
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing location.'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

