# WhatNowAI

A Flask-based multi-step onboarding application that helps users determine their next steps based on their location, interests, and social media presence. Features include automatic location detection, social media integration, text-to-speech for enhanced user experience, and intelligent background research using web scraping.

## Features

- **Multi-step Onboarding**: Smooth, animated progression through user information collection
- **Text-to-Speech Integration**: EdgeTTS provides voice guidance during onboarding steps
- **Voice Transcription**: AssemblyAI-powered voice input for activities
- **Location Detection**: Automatic geolocation with reverse geocoding
- **Social Media Integration**: Optional Twitter/X, Instagram, GitHub, and LinkedIn handle collection
- **Background Research**: Intelligent web scraping to gather relevant context about users and activities
- **Privacy-focused Search**: Uses DuckDuckGo for user research while respecting privacy
- **Responsive Design**: Modern, mobile-friendly interface
- **Modular Architecture**: Clean separation of concerns with service-based design

## Project Structure

```
WhatNowAI/
├── app.py                     # Main Flask application
├── routes.py                  # Flask routes and endpoints
├── config/
│   ├── __init__.py
│   └── settings.py           # Application configuration
├── services/
│   ├── __init__.py
│   ├── tts_service.py        # Text-to-Speech service
│   ├── voice_transcription.py # Voice input service
│   └── geocoding_service.py  # Location services
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Utility functions
├── searchmethods/
│   ├── __init__.py
│   ├── background_search.py  # Web scraping and search service
│   ├── README.md             # Search methods documentation
│   └── test_search.py        # Test script for search functionality
├── templates/
│   └── home.html             # Main template
├── static/
│   ├── css/
│   │   └── styles.css        # Styling
│   ├── js/
│   │   └── main.js           # Frontend logic
│   ├── images/
│   └── audio/                # Generated TTS audio files
├── requirements.txt          # Python dependencies
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd WhatNowAI
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5002`

3. Follow the multi-step onboarding process:
   - **Step 1**: Welcome screen with audio introduction
   - **Step 2**: Enter name and optional social media handles
   - **Step 3**: Describe what you want to do
   - **Step 4**: Share location (optional)
   - **Processing**: AI analyzes your information
   - **Results**: Personalized recommendations

## Technical Details

### TTS Integration
- Uses Microsoft EdgeTTS for natural voice synthesis
- Audio plays automatically during onboarding steps
- Temporary audio files are cleaned up automatically

### Voice Transcription
- AssemblyAI integration for speech-to-text
- Real-time voice input for activity descriptions
- WebRTC-based audio recording in the browser

### Background Research
- Intelligent web scraping using BeautifulSoup and requests
- Privacy-focused search using DuckDuckGo
- Multi-source data gathering:
  - General web search for user information
  - Social media profile analysis (GitHub, Twitter, LinkedIn)
  - Location-specific events and activities
  - Activity-related tutorials and resources
- Smart result summarization for personalized recommendations
- Rate limiting and error handling for responsible scraping

### Location Services
- Browser-based geolocation API
- OpenStreetMap Nominatim for reverse geocoding
- Privacy-focused with user consent

### Architecture
- **Service Layer**: Modular services for TTS, geocoding, and data processing
- **Configuration Management**: Centralized settings and logging
- **Error Handling**: Comprehensive error handling and logging
- **Responsive Design**: Mobile-first approach with smooth animations

## Dependencies

- **Flask**: Web framework
- **edge-tts**: Text-to-speech synthesis
- **requests**: HTTP library for API calls
- **beautifulsoup4**: HTML parsing (for future social media features)

## Configuration

Key configuration options in `config/settings.py`:
- **TTS Voice**: Default voice for text-to-speech
- **Audio Directory**: Location for temporary audio files
- **Logging**: Structured logging configuration
- **Flask Settings**: Debug mode, host, and port

## API Endpoints

- `GET /`: Main application page
- `POST /tts/introduction/<step>`: Generate TTS for onboarding steps
- `POST /submit`: Submit user information
- `POST /process`: Process user request
- `POST /geocode`: Reverse geocode coordinates
- `GET /audio/<audio_id>`: Serve generated audio files

## Development

The application follows Python best practices:
- Type hints for better code documentation
- Modular service architecture
- Comprehensive error handling and logging
- Clean separation of concerns

## License

[Add your license here]