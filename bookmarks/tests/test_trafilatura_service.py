import os
import tempfile
import gzip
from unittest import mock
from django.test import TestCase, override_settings
from bookmarks.services import trafilatura_extractor


class TrafilaturaExtractorTestCase(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_html_filepath = os.path.join(self.temp_dir, "test.html")

    def tearDown(self):
        # Clean up temp files
        if os.path.exists(self.temp_html_filepath):
            os.remove(self.temp_html_filepath)
        os.rmdir(self.temp_dir)

    def create_test_file(self):
        """Create a test HTML file"""
        content = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Test Content</h1>
    <p>This is test content.</p>
    <img src="/test.jpg" alt="Test image">
</body>
</html>"""
        with open(self.temp_html_filepath, "w") as f:
            f.write(content)

    def test_create_snapshot_success(self):
        """Test successful snapshot creation with trafilatura"""
        # Mock trafilatura functions
        mock_downloaded_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <article>
                <h1>Test Article</h1>
                <p>This is the main content of the article.</p>
                <img src="https://example.com/image.jpg" alt="Test image">
            </article>
        </body>
        </html>
        """
        
        mock_extracted_content = """
        <h1>Test Article</h1>
        <p>This is the main content of the article.</p>
        <img src="https://example.com/image.jpg" alt="Test image">
        """

        with mock.patch('trafilatura.fetch_url', return_value=mock_downloaded_content), \
             mock.patch('trafilatura.extract', return_value=mock_extracted_content), \
             mock.patch('trafilatura.extract_metadata') as mock_metadata, \
             mock.patch('requests.Session.get') as mock_get:
            
            # Mock metadata
            mock_meta = mock.Mock()
            mock_meta.title = "Test Article"
            mock_meta.author = "Test Author"
            mock_meta.date = "2024-01-01"
            mock_meta.sitename = "Test Site"
            mock_meta.description = "Test description"
            mock_metadata.return_value = mock_meta
            
            # Mock image download (simulate failure to test fallback)
            mock_response = mock.Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            # Test the function
            trafilatura_extractor.create_snapshot("https://example.com/test", self.temp_html_filepath)
            
            # Check if file was created
            self.assertTrue(os.path.exists(self.temp_html_filepath))
            
            # Check file content
            with open(self.temp_html_filepath, 'r') as f:
                content = f.read()
                self.assertIn("Test Article", content)
                self.assertIn("Archived Content", content)
                self.assertIn("https://example.com/test", content)
                self.assertIn("linkding + Trafilatura", content)

    def test_create_snapshot_with_image_embedding(self):
        """Test snapshot creation with successful image embedding"""
        mock_downloaded_content = """
        <html><body><p>Test content</p><img src="test.jpg" alt="Test"></body></html>
        """
        
        mock_extracted_content = """
        <p>Test content</p><img src="test.jpg" alt="Test">
        """

        # Mock successful image download
        mock_image_data = b'fake_image_data'
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/jpeg', 'content-length': '100'}
        mock_response.iter_content.return_value = [mock_image_data]

        with mock.patch('trafilatura.fetch_url', return_value=mock_downloaded_content), \
             mock.patch('trafilatura.extract', return_value=mock_extracted_content), \
             mock.patch('trafilatura.extract_metadata', return_value=mock.Mock(title="Test")), \
             mock.patch('requests.Session.get', return_value=mock_response):
            
            trafilatura_extractor.create_snapshot("https://example.com/test", self.temp_html_filepath)
            
            # Check if file was created and contains base64 image
            self.assertTrue(os.path.exists(self.temp_html_filepath))
            
            with open(self.temp_html_filepath, 'r') as f:
                content = f.read()
                self.assertIn("data:image/jpeg;base64,", content)

    def test_create_snapshot_failure(self):
        """Test snapshot creation failure handling"""
        with mock.patch('trafilatura.fetch_url', return_value=None):
            with self.assertRaises(trafilatura_extractor.TrafilaturaError):
                trafilatura_extractor.create_snapshot("https://example.com/test", self.temp_html_filepath)

    @override_settings(LD_TRAFILATURA_EMBED_IMAGES=False)
    def test_create_snapshot_without_image_embedding(self):
        """Test snapshot creation with image embedding disabled"""
        mock_downloaded_content = "<html><body><p>Test</p></body></html>"
        mock_extracted_content = "<p>Test</p>"

        with mock.patch('trafilatura.fetch_url', return_value=mock_downloaded_content), \
             mock.patch('trafilatura.extract', return_value=mock_extracted_content), \
             mock.patch('trafilatura.extract_metadata', return_value=mock.Mock(title="Test")):
            
            trafilatura_extractor.create_snapshot("https://example.com/test", self.temp_html_filepath)
            
            self.assertTrue(os.path.exists(self.temp_html_filepath))

    @override_settings(LD_TRAFILATURA_TIMEOUT_SEC=5)
    def test_custom_timeout_setting(self):
        """Test that custom timeout setting is respected"""
        extractor = trafilatura_extractor.TrafilaturaContentExtractor()
        self.assertEqual(extractor.timeout, 5)

    def test_html_escaping(self):
        """Test HTML escaping in metadata"""
        extractor = trafilatura_extractor.TrafilaturaContentExtractor()
        
        # Test various HTML entities
        test_cases = [
            ("Simple text", "Simple text"),
            ("Text with <tags>", "Text with &lt;tags&gt;"),
            ('Text with "quotes"', 'Text with &quot;quotes&quot;'),
            ("Text with 'apostrophes'", "Text with &#x27;apostrophes&#x27;"),
            ("Text with & ampersands", "Text with &amp; ampersands"),
        ]
        
        for input_text, expected_output in test_cases:
            self.assertEqual(extractor._escape_html(input_text), expected_output)
