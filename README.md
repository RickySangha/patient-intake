# Medical Intake AI Assistant

An AI-powered medical intake system that conducts preliminary patient interviews using voice interactions. The system uses Daily.co for video/audio communication, OpenAI for language processing, and Cartesia for text-to-speech.

## Features

- Voice-based patient intake interviews
- Specialty-specific assessment flows (Respiratory, Chest Pain, etc.)
- Emergency detection and routing
- Medical history collection
- Real-time transcription
- Automatic staff alerts for emergencies

## Prerequisites

- Python 3.10 or higher
- Daily.co API key
- OpenAI API key
- Cartesia API key

## Installation

1. Clone the repository:

2. Install dependencies using pipenv:

```bash
pipenv install -r requirements.txt
```

3. Rename the `.env.example` file to `.env` and add your API keys:

## Running the Application

1. Start the FastAPI server:

```bash
pipenv run python src/server.py
```

2. Access the application:

- Visit `http://localhost:7860` to create a new room
- Or use an existing room by visiting `http://localhost:7860?room_url=your_room_url`

## Project Structure

- `src/`
  - `agent/` - Core agent logic and conversation flows
    - `general_nodes/` - General conversation nodes (intake, history, etc.)
    - `specialty_nodes/` - Specialty-specific assessment flows
  - `config/` - Configuration files
  - `custom-services/` - Custom services not in pipecat framework
  - `server.py` - FastAPI server implementation
  - `bot.py` - Main bot implementation
  - `runner.py` - Configuration and setup utilities
