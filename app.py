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
        
        if not name or not activity:
            return jsonify({
                'success': False,
                'message': 'Missing name or activity information.'
            }), 400
        
        # TODO: Add your actual AI/processing logic here
        # This is a placeholder for now - simulate processing time
        import time
        time.sleep(3)  # Simulate processing delay
        
        # Placeholder response - replace with actual AI logic
        result = f"Great news, {name}! I've analyzed your request to {activity}. Here are some suggestions:\n\n" \
                f"1. Start by breaking down '{activity}' into smaller steps\n" \
                f"2. Set a timeline for completion\n" \
                f"3. Gather any resources you might need\n\n" \
                f"Would you like me to help you create a detailed plan?"
        
        return jsonify({
            'success': True,
            'result': result,
            'name': name,
            'activity': activity
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

