# SlideShare Downloader

## Overview
A Flask web application that allows users to download SlideShare presentations as PDF or PPTX files.

## Current State
- Fully functional web application
- Clean, modern, responsive UI
- Supports PDF and PPTX export formats
- Multiple scraping strategies for reliability

## Project Structure
```
.
├── app.py              # Flask backend with scraping and conversion logic
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend template with form and FAQ
├── static/
│   └── style.css       # Modern responsive styles
├── README.md           # Documentation
└── replit.md           # This file
```

## Key Features
1. **URL Validation**: Validates SlideShare URLs before processing
2. **Image Extraction**: Uses 6 different strategies to extract slide images
3. **PDF Conversion**: High-quality PDF using img2pdf
4. **PPTX Conversion**: PowerPoint with auto-fitted slides using python-pptx
5. **Real-time Status**: Loading states and success/error feedback

## Tech Stack
- Backend: Flask 2.2.5
- Web Scraping: BeautifulSoup4, Requests
- PDF Creation: img2pdf
- PPTX Creation: python-pptx
- Image Processing: Pillow 9.5.0
- Frontend: HTML5, CSS3, Vanilla JavaScript

## API Endpoints
- `GET /` - Main web interface
- `POST /download` - Download endpoint (JSON: url, format)
- `GET /health` - Health check

## Running the Application
The application runs on port 5000 with the command: `python app.py`

## Recent Changes
- 2025-11-27: Initial creation with all core features

## Known Limitations
- Cannot download private/login-required presentations
- SlideShare website changes may break scraping
- Large presentations take longer to process
