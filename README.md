# SlideShare Downloader

A web-based tool to download SlideShare presentations as PDF or PowerPoint (PPTX) files.

## How to Run on Replit

1. The application runs automatically when you click the "Run" button
2. Access the web interface at the provided URL
3. Paste a SlideShare URL and choose your download format

## How It Works

1. **URL Validation**: The tool validates that you've entered a valid SlideShare URL
2. **Image Extraction**: Multiple strategies are used to extract slide images from the presentation page:
   - Picture/source tag parsing
   - Image srcset attribute extraction
   - Data attribute scanning
   - Inline JSON parsing
   - Meta tag extraction
   - Regex pattern matching
3. **Image Download**: All slide images are downloaded and processed
4. **Format Conversion**:
   - **PDF**: Uses `img2pdf` to create a high-quality PDF document
   - **PPTX**: Uses `python-pptx` to create a PowerPoint presentation with auto-fitted slides

## Features

- Clean, modern responsive UI
- Support for PDF and PPTX output formats
- Multiple image extraction strategies for reliability
- Automatic slide ordering
- High-quality image preservation
- Real-time status updates

## Known Limitations

1. **Private Presentations**: Cannot download presentations that require login or are set to private
2. **Website Changes**: SlideShare may update their website structure, which could temporarily break image extraction
3. **Rate Limiting**: Making too many requests in a short time may result in temporary blocks
4. **Large Presentations**: Very large presentations may take longer to process
5. **Image Quality**: The output quality depends on the original slide image quality available on SlideShare

## Supported URL Formats

- `https://www.slideshare.net/username/presentation-name`
- `https://slideshare.net/username/presentation-name`
- Regional variants (pt., de., es., fr.)

## Technical Stack

- **Backend**: Flask (Python web framework)
- **Web Scraping**: BeautifulSoup4, Requests
- **PDF Creation**: img2pdf
- **PPTX Creation**: python-pptx
- **Image Processing**: Pillow

## Notes for Production

1. **Rate Limiting**: Implement rate limiting to prevent abuse
2. **Caching**: Consider caching downloaded presentations to reduce load
3. **Error Handling**: Add comprehensive logging for debugging
4. **Security**: Validate and sanitize all user inputs
5. **Legal**: Ensure compliance with SlideShare's Terms of Service
6. **Monitoring**: Set up monitoring for scraping failures

## Environment Variables

- `SESSION_SECRET`: Flask session secret key (optional, has default fallback)

## API Endpoints

- `GET /`: Main web interface
- `POST /download`: Download endpoint (accepts JSON with `url` and `format`)
- `GET /health`: Health check endpoint

## License

For educational purposes only. Please respect copyright and the original authors' rights.
