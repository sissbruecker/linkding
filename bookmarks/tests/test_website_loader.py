from unittest import mock
from bookmarks.services import website_loader

from django.test import TestCase


class MockStreamingResponse:
    def __init__(self, num_chunks, chunk_size, insert_head_after_chunk=None):
        self.chunks = []
        for index in range(num_chunks):
            chunk = ''.zfill(chunk_size)
            self.chunks.append(chunk.encode('utf-8'))

            if index == insert_head_after_chunk:
                self.chunks.append('</head>'.encode('utf-8'))

    def iter_content(self, **kwargs):
        return self.chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class WebsiteLoaderTestCase(TestCase):
    def setUp(self):
        # clear cached metadata before test run
        website_loader.load_website_metadata.cache_clear()

    def render_html_document(self, title, description, og=False):
        if not og:
            meta = f'<meta name="description" content="{description}">'
        else:
            meta = f'<meta property="og:description" content="{description}">'
        return f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            {meta}
        </head>
        <body></body>
        </html>
        '''

    def test_load_page_returns_content(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = MockStreamingResponse(num_chunks=10, chunk_size=1024)
            content = website_loader.load_page('https://example.com')

            expected_content_size = 10 * 1024
            self.assertEqual(expected_content_size, len(content))

    def test_load_page_limits_large_documents(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = MockStreamingResponse(num_chunks=10, chunk_size=1024 * 1000)
            content = website_loader.load_page('https://example.com')

            # Should have read six chunks, after which content exceeds the max of 5MB
            expected_content_size = 6 * 1024 * 1000
            self.assertEqual(expected_content_size, len(content))

    def test_load_page_stops_reading_at_end_of_head(self):
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = MockStreamingResponse(num_chunks=10, chunk_size=1024 * 1000,
                                                          insert_head_after_chunk=0)
            content = website_loader.load_page('https://example.com')

            # Should have read first chunk, and second chunk containing closing head tag
            expected_content_size = 1 * 1024 * 1000 + len('</head>')
            self.assertEqual(expected_content_size, len(content))

    def test_load_page_removes_bytes_after_end_of_head(self):
        with mock.patch('requests.get') as mock_get:
            mock_response = MockStreamingResponse(num_chunks=1, chunk_size=0)
            mock_response.chunks[0] = '<head>人</head>'.encode('utf-8')
            # add a single byte that can't be decoded to utf-8
            mock_response.chunks[0] += 0xff.to_bytes(1, 'big')
            mock_get.return_value = mock_response
            content = website_loader.load_page('https://example.com')

            # verify that byte after head was removed, content parsed as utf-8
            self.assertEqual(content, '<head>人</head>')

    def test_load_website_metadata(self):
        with mock.patch('bookmarks.services.website_loader.load_page') as mock_load_page:
            mock_load_page.return_value = self.render_html_document('test title', 'test description')
            metadata = website_loader.load_website_metadata('https://example.com')
            self.assertEqual('test title', metadata.title)
            self.assertEqual('test description', metadata.description)

    def test_load_website_metadata_trims_title_and_description(self):
        with mock.patch('bookmarks.services.website_loader.load_page') as mock_load_page:
            mock_load_page.return_value = self.render_html_document('  test title  ', '  test description  ')
            metadata = website_loader.load_website_metadata('https://example.com')
            self.assertEqual('test title', metadata.title)
            self.assertEqual('test description', metadata.description)

    def test_load_website_metadata_using_og_description(self):
        with mock.patch('bookmarks.services.website_loader.load_page') as mock_load_page:
            mock_load_page.return_value = self.render_html_document('test title', 'test description', og=True)
            metadata = website_loader.load_website_metadata('https://example.com')
            self.assertEqual('test title', metadata.title)
            self.assertEqual('test description', metadata.description)
