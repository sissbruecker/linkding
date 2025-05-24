import logging
import os
import requests
from urllib.parse import urljoin, urlparse
import base64
import gzip
import trafilatura
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class TrafilaturaError(Exception):
    pass


def create_snapshot(url: str, filepath: str):
    """
    Lightweight alternative to SingleFile using Trafilatura for content extraction.
    Maintains same signature for API compatibility.
    
    Args:
        url: The URL to archive
        filepath: The output file path (will be .html or .html.gz)
    """
    try:
        extractor = TrafilaturaContentExtractor()
        html_content = extractor.extract_and_create_html(url)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write to file (uncompressed first, as assets.py will handle gzip compression)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"Created Trafilatura snapshot: {filepath} ({len(html_content)} bytes)")
        
    except Exception as e:
        logger.error(f"Failed to create Trafilatura snapshot for {url}: {e}")
        raise TrafilaturaError(f"Failed to create snapshot: {e}")


class TrafilaturaContentExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': getattr(settings, 'LD_TRAFILATURA_USER_AGENT', 
                'Mozilla/5.0 (compatible; linkding archiver)'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Configure session timeout
        self.timeout = getattr(settings, 'LD_TRAFILATURA_TIMEOUT_SEC', 30)
        
        # Image embedding settings
        self.embed_images = getattr(settings, 'LD_TRAFILATURA_EMBED_IMAGES', True)
        self.max_image_size = getattr(settings, 'LD_TRAFILATURA_MAX_IMAGE_SIZE', 1024 * 1024)  # 1MB
        
    def extract_and_create_html(self, url: str) -> str:
        """Extract content and create a complete HTML file"""
        try:
            # Download page content
            logger.info(f"Downloading content from {url}")
            downloaded = trafilatura.fetch_url(url, config=self._get_trafilatura_config())
            
            if not downloaded:
                raise TrafilaturaError("Failed to download page content")
            
            # Extract main content without embedded metadata to avoid lxml errors
            content = trafilatura.extract(
                downloaded,
                include_images=True,
                include_links=True,
                include_tables=True,
                include_formatting=True,
                output_format='html',
                favor_precision=True,
                with_metadata=False  # We'll handle metadata separately
            )
            
            if not content:
                raise TrafilaturaError("Failed to extract readable content from page")
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(downloaded)
            
            # Process and embed images if enabled
            if self.embed_images:
                content = self._embed_images_in_content(content, url)
            
            # Create final HTML
            html_output = self._create_complete_html(content, metadata, url)
            
            return html_output
            
        except requests.RequestException as e:
            raise TrafilaturaError(f"Network error: {e}")
        except Exception as e:
            raise TrafilaturaError(f"Content extraction error: {e}")
    
    def _get_trafilatura_config(self):
        """Get Trafilatura configuration"""
        config = trafilatura.settings.use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", str(self.timeout))
        return config
    
    def _embed_images_in_content(self, content: str, base_url: str) -> str:
        """Download and embed images as base64 data URLs"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Handle both <img> and <graphic> tags (Trafilatura uses <graphic>)
            image_tags = soup.find_all(['img', 'graphic'])
            
            for img in image_tags:
                src = img.get('src')
                if not src:
                    continue
                
                # Skip if already a data URL
                if src.startswith('data:'):
                    continue
                
                try:
                    # Resolve relative URLs
                    img_url = urljoin(base_url, src)
                    
                    # Download image with size limit
                    response = self.session.get(
                        img_url, 
                        timeout=10, 
                        stream=True,
                        headers={'Referer': base_url}
                    )
                    
                    if response.status_code == 200:
                        # Check content length
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > self.max_image_size:
                            logger.debug(f"Skipping large image: {img_url} ({content_length} bytes)")
                            continue
                        
                        # Download with size limit
                        image_data = b''
                        downloaded_size = 0
                        
                        for chunk in response.iter_content(chunk_size=8192):
                            downloaded_size += len(chunk)
                            if downloaded_size > self.max_image_size:
                                logger.debug(f"Image too large, skipping: {img_url}")
                                break
                            image_data += chunk
                        else:
                            # Successfully downloaded within size limit
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            if content_type.startswith('image/'):
                                img_data_b64 = base64.b64encode(image_data).decode()
                                data_url = f"data:{content_type};base64,{img_data_b64}"
                                
                                # Convert <graphic> tags to proper <img> tags
                                if img.name == 'graphic':
                                    img.name = 'img'
                                    # Copy any existing attributes
                                    if 'title' in img.attrs:
                                        img['alt'] = img.get('title', '')
                                
                                img['src'] = data_url
                                logger.debug(f"Embedded image: {img_url} ({len(image_data)} bytes)")
                
                except Exception as e:
                    logger.debug(f"Failed to embed image {img_url}: {e}")
                    # Keep original src on failure
                    pass
            
            return str(soup)
            
        except Exception as e:
            logger.warning(f"Failed to embed images: {e}")
            return content
    
    def _create_complete_html(self, content: str, metadata, original_url: str) -> str:
        """Create a complete HTML document"""
        
        # Extract metadata safely, handle lists and non-string values
        def safe_extract(value, default=""):
            if value is None:
                return default
            if isinstance(value, list):
                return ', '.join(str(item) for item in value if item) or default
            return str(value) if value else default
        
        title = safe_extract(getattr(metadata, 'title', None), "Archived Page")
        author = safe_extract(getattr(metadata, 'author', None))
        date = safe_extract(getattr(metadata, 'date', None))
        site_name = safe_extract(getattr(metadata, 'sitename', None))
        description = safe_extract(getattr(metadata, 'description', None))
        
        # Current timestamp
        archived_at = timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Create clean HTML document
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)}</title>
    <meta name="description" content="{self._escape_html(description)}">
    <meta name="author" content="{self._escape_html(author)}">
    <meta name="archived-from" content="{self._escape_html(original_url)}">
    <meta name="archived-at" content="{archived_at}">
    <meta name="archived-with" content="linkding-trafilatura">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background: #fff;
        }}
        
        .archive-header {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 24px;
            font-size: 14px;
            color: #6c757d;
        }}
        
        .archive-header h2 {{
            margin: 0 0 8px 0;
            font-size: 16px;
            color: #495057;
        }}
        
        .archive-header a {{
            color: #007bff;
            text-decoration: none;
            word-break: break-all;
        }}
        
        .archive-header a:hover {{
            text-decoration: underline;
        }}
        
        .content h1, .content h2, .content h3, .content h4, .content h5, .content h6 {{
            color: #212529;
            margin-top: 24px;
            margin-bottom: 16px;
        }}
        
        .content h1 {{
            font-size: 2em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 8px;
        }}
        
        .content img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 16px 0;
        }}
        
        .content blockquote {{
            border-left: 4px solid #dfe2e5;
            margin: 16px 0;
            padding: 0 16px;
            color: #6a737d;
        }}
        
        .content code {{
            background: #f6f8fa;
            border-radius: 3px;
            font-size: 85%;
            margin: 0;
            padding: 2px 4px;
        }}
        
        .content pre {{
            background: #f6f8fa;
            border-radius: 6px;
            font-size: 85%;
            line-height: 1.45;
            overflow: auto;
            padding: 16px;
        }}
        
        .content table {{
            border-collapse: collapse;
            margin: 16px 0;
            width: 100%;
        }}
        
        .content th, .content td {{
            border: 1px solid #dfe2e5;
            padding: 8px 12px;
            text-align: left;
        }}
        
        .content th {{
            background: #f6f8fa;
            font-weight: 600;
        }}
        
        .content a {{
            color: #0366d6;
            text-decoration: none;
        }}
        
        .content a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="archive-header">
        <h2>📄 Archived Content</h2>
        <div><strong>Original URL:</strong> <a href="{self._escape_html(original_url)}" target="_blank" rel="noopener">{self._escape_html(original_url)}</a></div>
        {f'<div><strong>Site:</strong> {self._escape_html(site_name)}</div>' if site_name else ''}
        {f'<div><strong>Author:</strong> {self._escape_html(author)}</div>' if author else ''}
        {f'<div><strong>Published:</strong> {self._escape_html(str(date))}</div>' if date else ''}
        <div><strong>Archived:</strong> {archived_at}</div>
        <div><strong>Archived with:</strong> linkding + Trafilatura</div>
    </div>
    
    <main class="content">
        {content}
    </main>
</body>
</html>"""
        
        return html_template
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML entities in text"""
        if not text:
            return ""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))
