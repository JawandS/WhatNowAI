# API Setup Guide

This guide explains how to set up the required API keys for WhatNowAI's enhanced functionality.

## Required API Keys

### 1. Ticketmaster Discovery API
- **Purpose**: Find local events and activities
- **Sign up**: https://developer.ticketmaster.com/
- **Free tier**: 5,000 API calls per day
- **Environment variable**: `TICKETMASTER_API_KEY`

#### Setup:
1. Create an account at https://developer.ticketmaster.com/
2. Create a new app in your dashboard
3. Copy your Consumer Key (this is your API key)
4. Set the environment variable:
   ```bash
   export TICKETMASTER_API_KEY="your_api_key_here"
   ```

### 2. OpenAI API (Optional)
- **Purpose**: AI-powered activity categorization for better event matching
- **Sign up**: https://platform.openai.com/
- **Cost**: Pay-per-use (very minimal for this application)
- **Environment variable**: `OPENAI_API_KEY`

#### Setup:
1. Create an account at https://platform.openai.com/
2. Generate an API key in your dashboard
3. Set the environment variable:
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

### 3. AssemblyAI (Already configured)
- **Purpose**: Voice transcription
- **Environment variable**: `ASSEMBLY_AI_KEY`

### 4. HuggingFace (Already configured)
- **Purpose**: AI processing
- **Environment variable**: `HUGGINGFACE_TOKEN`

## Environment Variables Setup

Create a `.env` file in your project root:

```bash
# Ticketmaster API
TICKETMASTER_API_KEY=your_ticketmaster_key_here

# OpenAI API (optional)
OPENAI_API_KEY=your_openai_key_here

# Voice transcription
ASSEMBLY_AI_KEY=your_assemblyai_key_here

# AI processing
HUGGINGFACE_TOKEN=your_huggingface_token_here
```

Or set them directly in your environment:

```bash
# Linux/Mac
export TICKETMASTER_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

# Windows
set TICKETMASTER_API_KEY=your_key
set OPENAI_API_KEY=your_key
```

## Testing the Setup

1. Start the application:
   ```bash
   python app.py
   ```

2. Go through the onboarding process
3. After providing your location and activity, you should be redirected to the map
4. The map should show local events from Ticketmaster

## Troubleshooting

### No events showing on map:
- Check that `TICKETMASTER_API_KEY` is set correctly
- Verify your API key has sufficient quota
- Check the browser console for error messages

### Map not loading:
- Ensure you have a stable internet connection
- Check that location permissions are granted
- Verify the map tiles are loading (OpenStreetMap)

### API Key Issues:
- Verify the API keys are set as environment variables
- Restart the application after setting new environment variables
- Check the API provider's dashboard for usage and errors

## Future API Integrations

The mapping service is designed to support multiple event APIs:

- **Eventbrite**: Local event discovery
- **Meetup**: Community gatherings
- **Facebook Events**: Social events
- **Google Places**: Local business events

To add new APIs, implement the corresponding methods in `services/mapping_service.py` and update the event loading logic in `routes.py`.

## Rate Limiting

Be aware of API rate limits:
- **Ticketmaster**: 5,000 calls/day (free tier)
- **OpenAI**: Pay-per-use, very minimal cost for categorization
- **OpenStreetMap**: No API key required, community-supported

The application implements caching and request optimization to minimize API usage.
