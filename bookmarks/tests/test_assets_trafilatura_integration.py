import os
import tempfile
import gzip
from unittest import mock
from django.test import TestCase, override_settings
from bookmarks.tests.helpers import BookmarkFactoryMixin
from bookmarks.services import assets
from bookmarks.models import BookmarkAsset


class AssetServiceTrafilaturaTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = None  # Initialize user attribute for BookmarkFactoryMixin
        self.setup_temp_assets_dir()  # Set up temporary assets directory for testing
        self.bookmark = self.setup_bookmark()

    @override_settings(LD_ARCHIVER_TYPE='trafilatura')
    def test_create_snapshot_with_trafilatura(self):
        """Test that assets service uses Trafilatura when configured"""
        with mock.patch('bookmarks.services.trafilatura_extractor.create_snapshot') as mock_trafilatura, \
             mock.patch('bookmarks.services.singlefile.create_snapshot') as mock_singlefile:
            
            # Create mock file for trafilatura with gzipped content
            def create_mock_file(url, filepath):
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                html_content = f"<html><body><h1>Trafilatura Test</h1><p>URL: {url}</p></body></html>"
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(html_content)
            
            mock_trafilatura.side_effect = create_mock_file
            
            # Create snapshot asset
            asset = assets.create_snapshot_asset(self.bookmark)
            assets.create_snapshot(asset)
            
            # Verify Trafilatura was called, not SingleFile
            mock_trafilatura.assert_called_once()
            mock_singlefile.assert_not_called()
            
            # Verify asset was created successfully
            asset.refresh_from_db()
            self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
            self.assertTrue(asset.file.endswith('.html.gz'))
            self.assertTrue(asset.gzip)
            
            # Verify the bookmark's latest snapshot was updated
            self.bookmark.refresh_from_db()
            self.assertEqual(self.bookmark.latest_snapshot, asset)

    @override_settings(LD_ARCHIVER_TYPE='singlefile')  
    def test_create_snapshot_with_singlefile_default(self):
        """Test that assets service uses SingleFile by default"""
        with mock.patch('bookmarks.services.trafilatura_extractor.create_snapshot') as mock_trafilatura, \
             mock.patch('bookmarks.services.singlefile.create_snapshot') as mock_singlefile:
            
            # Create mock file for singlefile
            def create_mock_file(url, filepath):
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(f"<html><body><h1>SingleFile Test</h1><p>URL: {url}</p></body></html>")
            
            mock_singlefile.side_effect = create_mock_file
            
            # Create snapshot asset
            asset = assets.create_snapshot_asset(self.bookmark)
            assets.create_snapshot(asset)
            
            # Verify SingleFile was called, not Trafilatura
            mock_singlefile.assert_called_once()
            mock_trafilatura.assert_not_called()
            
            # Verify asset was created successfully
            asset.refresh_from_db()
            self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)

    @override_settings(LD_ARCHIVER_TYPE='trafilatura')
    def test_trafilatura_compression_format(self):
        """Test that Trafilatura output is properly compressed as gzip"""
        with mock.patch('bookmarks.services.trafilatura_extractor.create_snapshot') as mock_trafilatura:
            
            # Create mock HTML content
            test_content = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <div class="archive-header">
        <h2>📄 Archived Content</h2>
        <div><strong>Original URL:</strong> <a href="https://example.com">https://example.com</a></div>
    </div>
    <main class="content">
        <h1>Test Article</h1>
        <p>This is test content from Trafilatura.</p>
    </main>
</body>
</html>"""
            
            def create_mock_file(url, filepath):
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(test_content)
            
            mock_trafilatura.side_effect = create_mock_file
            
            # Create snapshot asset
            asset = assets.create_snapshot_asset(self.bookmark)
            assets.create_snapshot(asset)
            
            # Verify the file was created and is gzipped
            asset.refresh_from_db()
            self.assertEqual(asset.status, BookmarkAsset.STATUS_COMPLETE)
            self.assertTrue(asset.gzip)
            
            # Verify we can read the gzipped content from the asset file
            if self.has_asset_file(asset):
                content = self.read_asset_file(asset)
                content_str = gzip.decompress(content).decode('utf-8')
                self.assertIn("Test Article", content_str)
                self.assertIn("Archived Content", content_str)
                self.assertIn("Trafilatura", content_str)

    @override_settings(LD_ARCHIVER_TYPE='invalid_archiver')
    def test_invalid_archiver_falls_back_to_singlefile(self):
        """Test that invalid archiver type falls back to SingleFile"""
        with mock.patch('bookmarks.services.trafilatura_extractor.create_snapshot') as mock_trafilatura, \
             mock.patch('bookmarks.services.singlefile.create_snapshot') as mock_singlefile:
            
            def create_mock_file(url, filepath):
                # Ensure directory exists
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(f"<html><body><h1>Fallback Test</h1></body></html>")
            
            mock_singlefile.side_effect = create_mock_file
            
            # Create snapshot asset
            asset = assets.create_snapshot_asset(self.bookmark)
            assets.create_snapshot(asset)
            
            # Should fall back to SingleFile for invalid archiver type
            mock_singlefile.assert_called_once()
            mock_trafilatura.assert_not_called()
