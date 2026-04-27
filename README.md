# Grok Aurora Studio

Unlimited image and video generation powered by Grok Aurora, with browser-based authentication and real-time generation capabilities.

## Features

- **Unlimited Image Generation**: Generate unlimited high-quality images using Grok Aurora
- **Video Generation**: Create videos with custom prompts and parameters
- **Browser-Based Auth**: Automatic session detection from your Grok account
- **Real-Time Streaming**: Watch generation progress in real-time
- **Simple Web UI**: Clean, intuitive interface for creating content

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py

# Open in browser
# http://localhost:8000
```

## Architecture

- **Backend**: FastAPI + WebSocket for real-time updates
- **Frontend**: Vanilla JS + Tailwind CSS
- **Authentication**: Browser session bridge via Grok website
- **Generation**: Direct integration with Grok Aurora API

## Project Structure

```
grok/
├── app.py                 # FastAPI server
├── grok_client.py         # Grok API client wrapper
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html        # Main UI
│   ├── style.css         # Styling
│   └── app.js            # Frontend logic
└── README.md
```

## Usage

1. Keep Grok website open in your browser (for session bridge)
2. Open the web UI at `http://localhost:8000`
3. Enter your prompt and click generate
4. Watch the real-time progress and download results

## License

Personal use only
