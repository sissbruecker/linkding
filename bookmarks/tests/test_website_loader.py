from unittest import mock

import ipaddress

from django.test import TestCase

from bookmarks.services import website_loader


class MockStreamingResponse:
    def __init__(self, num_chunks, chunk_size, insert_head_after_chunk=None):
        self.chunks = []
        for index in range(num_chunks):
            chunk = "".zfill(chunk_size)
            self.chunks.append(chunk.encode("utf-8"))

            if index == insert_head_after_chunk:
                self.chunks.append(b"</head>")

        self.is_redirect = False

    def iter_content(self, **kwargs):
        return self.chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def fake_getaddrinfo(host, port, **kwargs):
    """Resolve literal IPs to themselves, hostnames to a safe public address."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = ipaddress.ip_address("93.184.216.34")
    return [(0, 0, 0, "", (str(ip), 0))]


class WebsiteLoaderTestCase(TestCase):
    def setUp(self):
        # clear cached metadata before test run
        website_loader._load_website_metadata_cached.cache_clear()
        # stub DNS so the SSRF guard resolves hosts deterministically
        self.dns_patcher = mock.patch(
            "bookmarks.services.website_loader.socket.getaddrinfo",
            side_effect=fake_getaddrinfo,
        )
        self.dns_patcher.start()
        self.addCleanup(self.dns_patcher.stop)

    def render_html_document(
        self, title, description="", og_description="", og_image=""
    ):
        meta_description = (
            f'<meta name="description" content="{description}">' if description else ""
        )
        meta_og_description = (
            f'<meta property="og:description" content="{og_description}">'
            if og_description
            else ""
        )
        meta_og_image = (
            f'<meta property="og:image" content="{og_image}">' if og_image else ""
        )
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            {meta_description}
            {meta_og_description}
            {meta_og_image}
        </head>
        <body></body>
        </html>
        """

    def test_load_page_returns_content(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = MockStreamingResponse(
                num_chunks=10, chunk_size=1024
            )
            content = website_loader.load_page("https://example.com")

            expected_content_size = 10 * 1024
            self.assertEqual(expected_content_size, len(content))

    def test_load_page_limits_large_documents(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = MockStreamingResponse(
                num_chunks=10, chunk_size=1024 * 1000
            )
            content = website_loader.load_page("https://example.com")

            # Should have read six chunks, after which content exceeds the max of 5MB
            expected_content_size = 6 * 1024 * 1000
            self.assertEqual(expected_content_size, len(content))

    def test_load_page_stops_reading_at_end_of_head(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = MockStreamingResponse(
                num_chunks=10, chunk_size=1024 * 1000, insert_head_after_chunk=0
            )
            content = website_loader.load_page("https://example.com")

            # Should have read first chunk, and second chunk containing closing head tag
            expected_content_size = 1 * 1024 * 1000 + len("</head>")
            self.assertEqual(expected_content_size, len(content))

    def test_load_page_removes_bytes_after_end_of_head(self):
        with mock.patch("requests.request") as mock_request:
            mock_response = MockStreamingResponse(num_chunks=1, chunk_size=0)
            mock_response.chunks[0] = "<head>人</head>".encode()
            # add a single byte that can't be decoded to utf-8
            mock_response.chunks[0] += 0xFF.to_bytes(1, "big")
            mock_request.return_value = mock_response
            content = website_loader.load_page("https://example.com")

            # verify that byte after head was removed, content parsed as utf-8
            self.assertEqual(content, "<head>人</head>")

    def test_load_website_metadata(self):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "test title", "test description"
            )
            metadata = website_loader.load_website_metadata("https://example.com")
            self.assertEqual("test title", metadata.title)
            self.assertEqual("test description", metadata.description)
            self.assertIsNone(metadata.preview_image)

    def test_load_website_metadata_trims_title_and_description(self):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "  test title  ", "  test description  "
            )
            metadata = website_loader.load_website_metadata("https://example.com")
            self.assertEqual("test title", metadata.title)
            self.assertEqual("test description", metadata.description)

    def test_load_website_metadata_using_og_description(self):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "test title", "", og_description="test og description"
            )
            metadata = website_loader.load_website_metadata("https://example.com")
            self.assertEqual("test title", metadata.title)
            self.assertEqual("test og description", metadata.description)

    def test_load_website_metadata_using_og_image(self):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "test title", og_image="http://example.com/image.jpg"
            )
            metadata = website_loader.load_website_metadata("https://example.com")
            self.assertEqual("http://example.com/image.jpg", metadata.preview_image)

    def test_load_website_metadata_gets_absolute_og_image_path_when_path_starts_with_dots(
        self,
    ):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "test title", og_image="../image.jpg"
            )
            metadata = website_loader.load_website_metadata(
                "https://example.com/a/b/page.html"
            )
            self.assertEqual("https://example.com/a/image.jpg", metadata.preview_image)

    def test_load_website_metadata_gets_absolute_og_image_path_when_path_starts_with_slash(
        self,
    ):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "test title", og_image="/image.jpg"
            )
            metadata = website_loader.load_website_metadata(
                "https://example.com/a/b/page.html"
            )
            self.assertEqual("https://example.com/image.jpg", metadata.preview_image)

    def test_load_website_metadata_prefers_description_over_og_description(self):
        with mock.patch(
            "bookmarks.services.website_loader.load_page"
        ) as mock_load_page:
            mock_load_page.return_value = self.render_html_document(
                "test title", "test description", og_description="test og description"
            )
            metadata = website_loader.load_website_metadata("https://example.com")
            self.assertEqual("test title", metadata.title)
            self.assertEqual("test description", metadata.description)

    def test_website_metadata_ignore_cache(self):
        expected_html = '<html><head><title>Test Title</title><meta name="description" content="Test Description"><meta property="og:image" content="/images/test.jpg"></head></html>'

        with mock.patch.object(
            website_loader, "load_page", return_value=expected_html
        ) as mock_load_page:
            website_loader.load_website_metadata("https://example.com")
            mock_load_page.assert_called_once()

            website_loader.load_website_metadata("https://example.com")
            mock_load_page.assert_called_once()

            website_loader.load_website_metadata(
                "https://example.com", ignore_cache=True
            )
            self.assertEqual(mock_load_page.call_count, 2)

    def test_load_page_rejects_loopback_address(self):
        with mock.patch("requests.request") as mock_request:
            with self.assertRaises(ValueError):
                website_loader.load_page("http://127.0.0.1:8080/internal")
            mock_request.assert_not_called()

    def test_load_page_rejects_private_ipv4(self):
        with mock.patch("requests.request") as mock_request:
            with self.assertRaises(ValueError):
                website_loader.load_page("http://10.0.0.5/")
            mock_request.assert_not_called()

    def test_load_page_rejects_cloud_metadata_address(self):
        with mock.patch("requests.request") as mock_request:
            with self.assertRaises(ValueError):
                website_loader.load_page("http://169.254.169.254/latest/meta-data/")
            mock_request.assert_not_called()

    def test_load_page_rejects_non_http_scheme(self):
        with mock.patch("requests.request") as mock_request:
            with self.assertRaises(ValueError):
                website_loader.load_page("file:///etc/passwd")
            mock_request.assert_not_called()

    def test_load_page_rejects_redirect_to_internal_address(self):
        def side_effect(method, url, **kwargs):
            if url == "http://public.example/":
                response = mock.Mock()
                response.is_redirect = True
                response.headers = {"Location": "http://127.0.0.1:8080/internal"}
                return response
            raise AssertionError(f"Unexpected request to disallowed URL: {url}")

        with mock.patch("requests.request", side_effect=side_effect) as mock_request:
            with self.assertRaises(ValueError):
                website_loader.load_page("http://public.example/")
            # only the initial public URL should have been requested
            self.assertEqual(
                [call.args[0:2] for call in mock_request.call_args_list],
                [("get", "http://public.example/")],
            )


class ContentTypeDetectionTestCase(TestCase):
    def setUp(self):
        self.dns_patcher = mock.patch(
            "bookmarks.services.website_loader.socket.getaddrinfo",
            side_effect=fake_getaddrinfo,
        )
        self.dns_patcher.start()
        self.addCleanup(self.dns_patcher.stop)

    def make_response(self, status_code=200, headers=None, is_redirect=False):
        response = mock.Mock()
        response.status_code = status_code
        response.headers = headers or {}
        response.is_redirect = is_redirect
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        return response

    def test_detect_content_type_returns_content_type_from_head_request(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = self.make_response(
                headers={"Content-Type": "application/pdf"}
            )

            result = website_loader.detect_content_type("https://example.com/doc.pdf")

            self.assertEqual(result, "application/pdf")
            mock_request.assert_called_once()

    def test_detect_content_type_strips_charset(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = self.make_response(
                headers={"Content-Type": "text/html; charset=utf-8"}
            )

            result = website_loader.detect_content_type("https://example.com")

            self.assertEqual(result, "text/html")

    def test_detect_content_type_returns_lowercase(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = self.make_response(
                headers={"Content-Type": "Application/PDF"}
            )

            result = website_loader.detect_content_type("https://example.com/doc.pdf")

            self.assertEqual(result, "application/pdf")

    def test_detect_content_type_falls_back_to_get_when_head_fails(self):
        import requests

        def side_effect(method, url, **kwargs):
            if method == "head":
                raise requests.RequestException("HEAD failed")
            return self.make_response(headers={"Content-Type": "application/pdf"})

        with mock.patch("requests.request", side_effect=side_effect) as mock_request:
            result = website_loader.detect_content_type("https://example.com/doc.pdf")

            self.assertEqual(result, "application/pdf")
            self.assertEqual(mock_request.call_count, 2)

    def test_detect_content_type_returns_none_when_both_head_and_get_fail(self):
        import requests

        with mock.patch(
            "requests.request", side_effect=requests.RequestException("GET failed")
        ) as mock_request:
            result = website_loader.detect_content_type("https://example.com")

            self.assertIsNone(result)

    def test_detect_content_type_returns_none_for_non_200_status(self):
        def side_effect(method, url, **kwargs):
            return self.make_response(status_code=404)

        with mock.patch("requests.request", side_effect=side_effect) as mock_request:
            result = website_loader.detect_content_type("https://example.com")

            self.assertIsNone(result)

    def test_is_pdf_content_type(self):
        self.assertTrue(website_loader.is_pdf_content_type("application/pdf"))
        self.assertTrue(website_loader.is_pdf_content_type("application/x-pdf"))
        self.assertFalse(website_loader.is_pdf_content_type("text/html"))
        self.assertFalse(website_loader.is_pdf_content_type(None))
        self.assertFalse(website_loader.is_pdf_content_type(""))
