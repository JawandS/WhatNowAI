# WhatNowAI

A Flask-based multi-step onboarding application that helps users determine their next steps based on their location, interests, and social media presence. Features include automatic location detection, social media integration, and text-to-speech for enhanced user experience.

## Features

- **Multi-step Onboarding**: Smooth, animated progression through user information collection
- **Text-to-Speech Integration**: EdgeTTS provides voice guidance during onboarding steps
- **Location Detection**: Automatic geolocation with reverse geocoding
- **Social Media Integration**: Optional Twitter/X and Instagram handle collection
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
│   └── geocoding_service.py  # Location services
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Utility functions
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