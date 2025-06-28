# WhatNowAI

A Flask-based multi-step onboarding application that helps users discover local events and activities based on their location, interests, and preferences. Features intelligent event discovery, interactive maps, and personalized recommendations.

## Features

- **Multi-step Onboarding**: Smooth, animated progression through user information collection
- **Text-to-Speech Integration**: EdgeTTS provides voice guidance during onboarding steps
- **Event Discovery**: Ticketmaster API integration for finding local events and activities
- **Interactive Maps**: Visual display of nearby events with filtering and search capabilities
- **Location Detection**: Automatic geolocation with reverse geocoding
- **Social Media Integration**: Optional social media handle collection for enhanced recommendations
- **Background Research**: Intelligent web scraping to gather relevant context about users and activities
- **Privacy-focused Search**: Uses DuckDuckGo for user research while respecting privacy
- **Responsive Design**: Modern, mobile-friendly interface with optimized scrolling
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
│   ├── geocoding_service.py  # Location services
│   ├── ticketmaster_service.py # Event discovery service
│   └── mapping_service.py    # Map and marker management
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Utility functions
├── searchmethods/
│   ├── __init__.py
│   ├── background_search.py  # Web scraping and search service
│   └── README.md             # Search methods documentation
├── templates/
│   ├── home.html             # Onboarding template
│   └── map.html              # Interactive map template
├── static/
│   ├── css/
│   │   ├── styles.css        # Main styling
│   │   └── map.css           # Map-specific styling
│   ├── js/
│   │   ├── main.js           # Onboarding logic
│   │   └── map.js            # Map functionality
│   ├── images/
│   └── audio/                # Generated TTS audio files
├── requirements.txt          # Python dependencies
├── secrets.txt               # API keys and secrets
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
   - **Map View**: Interactive map showing local events and activities

## Technical Details

### Event Discovery
- Ticketmaster API integration for real-time event data
- Event categorization (music, sports, arts, family, etc.)
- Location-based filtering and search capabilities
- Event details including pricing, venue, and ticketing information

### Interactive Maps
- Leaflet.js for interactive map visualization
- Custom markers for different event categories
- Real-time event filtering and search
- Responsive design optimized for mobile and desktop

### Text-to-Speech Integration
- Uses Microsoft EdgeTTS for natural voice synthesis
- Audio plays automatically during onboarding steps
- Temporary audio files are cleaned up automatically

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
- **Service Layer**: Modular services for TTS, geocoding, events, and mapping
- **Configuration Management**: Centralized settings and API key management
- **Error Handling**: Comprehensive error handling and logging
- **Responsive Design**: Mobile-first approach with optimized scrolling

## Dependencies

- **Flask**: Web framework for backend API
- **edge-tts**: Text-to-speech synthesis
- **requests**: HTTP library for API calls and web scraping
- **beautifulsoup4**: HTML parsing for web scraping
- **Leaflet.js**: Interactive map visualization (frontend)
- **Bootstrap 5**: Responsive UI framework (frontend)

## Configuration

Key configuration options in `config/settings.py`:
- **TTS Voice**: Default voice for text-to-speech
- **Audio Directory**: Location for temporary audio files
- **API Keys**: Ticketmaster, OpenAI, and other service credentials
- **Logging**: Structured logging configuration
- **Flask Settings**: Debug mode, host, and port

## API Endpoints

### Core Application
- `GET /`: Main onboarding page
- `GET /map`: Interactive map page

### Onboarding & Processing
- `POST /tts/introduction/<step>`: Generate TTS for onboarding steps
- `POST /submit`: Submit user information
- `POST /process`: Process user request and redirect to map

### Location & Events
- `POST /geocode`: Reverse geocode coordinates
- `POST /map/events`: Get events for map display
- `POST /map/search`: Search events on the map

### Audio & Assets
- `GET /audio/<audio_id>`: Serve generated audio files

## Development

The application follows Python best practices:
- Type hints for better code documentation
- Modular service architecture
- Comprehensive error handling and logging
- Clean separation of concerns

## License

[Add your license here]