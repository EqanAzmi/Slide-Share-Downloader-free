import os
import re
import io
import tempfile
import uuid
from urllib.parse import urlparse

from flask import Flask, render_template, request, send_file, jsonify
import requests
from bs4 import BeautifulSoup
from PIL import Image
import img2pdf
from pptx import Presentation
from pptx.util import Inches, Pt

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "slideshare-downloader-secret-key")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def validate_slideshare_url(url):
    """Validate that the URL is a valid SlideShare URL."""
    if not url:
        return False, "Please provide a URL"
    
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ['www.slideshare.net', 'slideshare.net', 'pt.slideshare.net', 'de.slideshare.net', 'es.slideshare.net', 'fr.slideshare.net']:
            return False, "Please provide a valid SlideShare URL (https://www.slideshare.net/...)"
        if not parsed.path or parsed.path == '/':
            return False, "Invalid SlideShare presentation URL"
        return True, "Valid URL"
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def extract_slide_images(url):
    """Extract slide image URLs from a SlideShare presentation."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        image_urls = []
        
        strategies = [
            extract_from_picture_tags,
            extract_from_img_srcset,
            extract_from_data_attributes,
            extract_from_script_json,
            extract_from_meta_tags,
            extract_from_regex_patterns,
        ]
        
        for strategy in strategies:
            try:
                urls = strategy(soup, html_content)
                if urls and len(urls) > 0:
                    image_urls = urls
                    break
            except Exception:
                continue
        
        if not image_urls:
            return None, "Could not find slide images. SlideShare may have changed their format or the presentation may be private."
        
        image_urls = clean_and_dedupe_urls(image_urls)
        
        if len(image_urls) == 0:
            return None, "No valid slide images found"
        
        return image_urls, f"Found {len(image_urls)} slides"
        
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return None, f"Failed to fetch presentation: {str(e)}"
    except Exception as e:
        return None, f"Error extracting slides: {str(e)}"


def extract_from_picture_tags(soup, html_content):
    """Extract images from picture/source tags."""
    urls = []
    picture_tags = soup.find_all('picture')
    for picture in picture_tags:
        sources = picture.find_all('source')
        for source in sources:
            srcset = source.get('srcset', '')
            if srcset and 'slide' in srcset.lower():
                url = srcset.split(',')[0].split(' ')[0].strip()
                if url:
                    urls.append(url)
    return urls


def extract_from_img_srcset(soup, html_content):
    """Extract images from img srcset attributes."""
    urls = []
    images = soup.find_all('img')
    for img in images:
        srcset = img.get('srcset', '') or img.get('data-srcset', '')
        src = img.get('src', '') or img.get('data-src', '')
        
        if srcset and ('slide' in srcset.lower() or 'image' in srcset.lower()):
            parts = srcset.split(',')
            for part in parts:
                url = part.strip().split(' ')[0]
                if url and url.startswith('http'):
                    urls.append(url)
        elif src and ('slide' in src.lower() or 'image' in src.lower()):
            if src.startswith('http'):
                urls.append(src)
    return urls


def extract_from_data_attributes(soup, html_content):
    """Extract images from data attributes."""
    urls = []
    elements = soup.find_all(attrs={'data-full': True})
    for elem in elements:
        url = elem.get('data-full')
        if url and url.startswith('http'):
            urls.append(url)
    
    elements = soup.find_all(attrs={'data-normal': True})
    for elem in elements:
        url = elem.get('data-normal')
        if url and url.startswith('http'):
            urls.append(url)
    
    return urls


def extract_from_script_json(soup, html_content):
    """Extract images from inline JSON data in script tags."""
    urls = []
    
    patterns = [
        r'"slideImageUrl"\s*:\s*"([^"]+)"',
        r'"imageUrl"\s*:\s*"([^"]+)"',
        r'"full"\s*:\s*"([^"]+)"',
        r'"normal"\s*:\s*"([^"]+)"',
        r'"slide_image"\s*:\s*"([^"]+)"',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        for match in matches:
            url = match.replace('\\u002F', '/').replace('\\/', '/')
            if url.startswith('http'):
                urls.append(url)
    
    return urls


def extract_from_meta_tags(soup, html_content):
    """Extract images from meta tags."""
    urls = []
    meta_tags = soup.find_all('meta', property=re.compile('og:image'))
    for meta in meta_tags:
        content = meta.get('content', '')
        if content and content.startswith('http'):
            urls.append(content)
    return urls


def extract_from_regex_patterns(soup, html_content):
    """Extract images using regex patterns as fallback."""
    urls = []
    
    patterns = [
        r'https?://[^"\'\s]+\.(?:jpg|jpeg|png|webp)(?:\?[^"\'\s]*)?',
        r'https?://image\.slidesharecdn\.com/[^"\'\s]+',
        r'https?://cdn\.slidesharecdn\.com/[^"\'\s]+\.(?:jpg|jpeg|png)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for url in matches:
            if 'slide' in url.lower() or 'image' in url.lower():
                urls.append(url)
    
    return urls


def clean_and_dedupe_urls(urls):
    """Clean and deduplicate image URLs, preferring highest quality."""
    seen = set()
    cleaned = []
    
    for url in urls:
        url = url.replace('\\u002F', '/').replace('\\/', '/')
        
        base_url = re.sub(r'\?.*$', '', url)
        
        if base_url in seen:
            continue
        
        if not url.startswith('http'):
            continue
            
        if 'avatar' in url.lower() or 'profile' in url.lower() or 'logo' in url.lower():
            continue
        
        seen.add(base_url)
        cleaned.append(url)
    
    def get_slide_number(url):
        match = re.search(r'[-_](\d+)[-_\.]', url)
        if match:
            return int(match.group(1))
        return 0
    
    cleaned.sort(key=get_slide_number)
    
    return cleaned


def download_images(image_urls):
    """Download images from URLs and return as PIL Image objects."""
    images = []
    
    for url in image_urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            img = Image.open(io.BytesIO(response.content))
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
            
        except Exception as e:
            print(f"Failed to download image {url}: {str(e)}")
            continue
    
    return images


def create_pdf(images):
    """Create a PDF from a list of PIL Image objects."""
    if not images:
        return None, "No images to convert"
    
    try:
        pdf_bytes = io.BytesIO()
        
        image_bytes_list = []
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr.seek(0)
            image_bytes_list.append(img_byte_arr.read())
        
        pdf_content = img2pdf.convert(image_bytes_list)
        pdf_bytes.write(pdf_content)
        pdf_bytes.seek(0)
        
        return pdf_bytes, "PDF created successfully"
        
    except Exception as e:
        return None, f"Failed to create PDF: {str(e)}"


def create_pptx(images):
    """Create a PPTX from a list of PIL Image objects."""
    if not images:
        return None, "No images to convert"
    
    try:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        
        blank_layout = prs.slide_layouts[6]
        
        for img in images:
            slide = prs.slides.add_slide(blank_layout)
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            img_width, img_height = img.size
            img_aspect = img_width / img_height
            slide_aspect = 13.333 / 7.5
            
            if img_aspect > slide_aspect:
                width = Inches(13.333)
                height = Inches(13.333 / img_aspect)
                left = Inches(0)
                top = Inches((7.5 - 13.333 / img_aspect) / 2)
            else:
                height = Inches(7.5)
                width = Inches(7.5 * img_aspect)
                left = Inches((13.333 - 7.5 * img_aspect) / 2)
                top = Inches(0)
            
            slide.shapes.add_picture(img_byte_arr, left, top, width, height)
        
        pptx_bytes = io.BytesIO()
        prs.save(pptx_bytes)
        pptx_bytes.seek(0)
        
        return pptx_bytes, "PPTX created successfully"
        
    except Exception as e:
        return None, f"Failed to create PPTX: {str(e)}"


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    """Handle the download request."""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        format_type = data.get('format', 'pdf').lower()
        
        is_valid, message = validate_slideshare_url(url)
        if not is_valid:
            return jsonify({'success': False, 'error': message}), 400
        
        if format_type not in ['pdf', 'pptx']:
            return jsonify({'success': False, 'error': 'Invalid format. Choose PDF or PPTX'}), 400
        
        image_urls, extract_message = extract_slide_images(url)
        if not image_urls:
            return jsonify({'success': False, 'error': extract_message}), 400
        
        images = download_images(image_urls)
        if not images:
            return jsonify({'success': False, 'error': 'Failed to download slide images'}), 400
        
        parsed_url = urlparse(url)
        filename_base = parsed_url.path.split('/')[-1] or 'presentation'
        filename_base = re.sub(r'[^\w\-]', '_', filename_base)
        
        if format_type == 'pdf':
            file_bytes, create_message = create_pdf(images)
            if not file_bytes:
                return jsonify({'success': False, 'error': create_message}), 500
            
            return send_file(
                file_bytes,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{filename_base}.pdf'
            )
        else:
            file_bytes, create_message = create_pptx(images)
            if not file_bytes:
                return jsonify({'success': False, 'error': create_message}), 500
            
            return send_file(
                file_bytes,
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                as_attachment=True,
                download_name=f'{filename_base}.pptx'
            )
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
