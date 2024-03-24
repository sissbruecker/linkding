from django.test import TestCase, override_settings


class MetadataViewTestCase(TestCase):

    def test_default_manifest(self):
        response = self.client.get("/manifest.json")

        self.assertEqual(response.status_code, 200)

        response_body = response.json()
        expected_body = {
            "short_name": "linkding",
            "name": "linkding",
            "description": "Self-hosted bookmark service",
            "start_url": "bookmarks",
            "display": "standalone",
            "scope": "/",
            "theme_color": "#5856e0",
            "background_color": "#ffffff",
            "icons": [
                {
                    "src": "/static/logo.svg",
                    "type": "image/svg+xml",
                    "sizes": "512x512",
                    "purpose": "any",
                },
                {
                    "src": "/static/logo-512.png",
                    "type": "image/png",
                    "sizes": "512x512",
                    "purpose": "any",
                },
                {
                    "src": "/static/logo-192.png",
                    "type": "image/png",
                    "sizes": "192x192",
                    "purpose": "any",
                },
                {
                    "src": "/static/maskable-logo.svg",
                    "type": "image/svg+xml",
                    "sizes": "512x512",
                    "purpose": "maskable",
                },
                {
                    "src": "/static/maskable-logo-512.png",
                    "type": "image/png",
                    "sizes": "512x512",
                    "purpose": "maskable",
                },
                {
                    "src": "/static/maskable-logo-192.png",
                    "type": "image/png",
                    "sizes": "192x192",
                    "purpose": "maskable",
                },
            ],
            "shortcuts": [
                {
                    "name": "Add bookmark",
                    "url": "/bookmarks/new",
                },
                {
                    "name": "Archived",
                    "url": "/bookmarks/archived",
                },
                {
                    "name": "Unread",
                    "url": "/bookmarks?unread=yes",
                },
                {
                    "name": "Untagged",
                    "url": "/bookmarks?q=!untagged",
                },
                {
                    "name": "Shared",
                    "url": "/bookmarks/shared",
                },
            ],
            "screenshots": [
                {
                    "src": "/static/linkding-screenshot.png",
                    "type": "image/png",
                    "sizes": "2158x1160",
                    "form_factor": "wide",
                }
            ],
            "share_target": {
                "action": "/bookmarks/new",
                "method": "GET",
                "enctype": "application/x-www-form-urlencoded",
                "params": {
                    "url": "url",
                    "text": "url",
                    "title": "title",
                },
            },
        }
        self.assertDictEqual(response_body, expected_body)

    @override_settings(LD_CONTEXT_PATH="linkding/")
    def test_manifest_respects_context_path(self):
        response = self.client.get("/manifest.json")

        self.assertEqual(response.status_code, 200)

        response_body = response.json()
        expected_body = {
            "short_name": "linkding",
            "name": "linkding",
            "description": "Self-hosted bookmark service",
            "start_url": "bookmarks",
            "display": "standalone",
            "scope": "/linkding/",
            "theme_color": "#5856e0",
            "background_color": "#ffffff",
            "icons": [
                {
                    "src": "/linkding/static/logo.svg",
                    "type": "image/svg+xml",
                    "sizes": "512x512",
                    "purpose": "any",
                },
                {
                    "src": "/linkding/static/logo-512.png",
                    "type": "image/png",
                    "sizes": "512x512",
                    "purpose": "any",
                },
                {
                    "src": "/linkding/static/logo-192.png",
                    "type": "image/png",
                    "sizes": "192x192",
                    "purpose": "any",
                },
                {
                    "src": "/linkding/static/maskable-logo.svg",
                    "type": "image/svg+xml",
                    "sizes": "512x512",
                    "purpose": "maskable",
                },
                {
                    "src": "/linkding/static/maskable-logo-512.png",
                    "type": "image/png",
                    "sizes": "512x512",
                    "purpose": "maskable",
                },
                {
                    "src": "/linkding/static/maskable-logo-192.png",
                    "type": "image/png",
                    "sizes": "192x192",
                    "purpose": "maskable",
                },
            ],
            "shortcuts": [
                {
                    "name": "Add bookmark",
                    "url": "/linkding/bookmarks/new",
                },
                {
                    "name": "Archived",
                    "url": "/linkding/bookmarks/archived",
                },
                {
                    "name": "Unread",
                    "url": "/linkding/bookmarks?unread=yes",
                },
                {
                    "name": "Untagged",
                    "url": "/linkding/bookmarks?q=!untagged",
                },
                {
                    "name": "Shared",
                    "url": "/linkding/bookmarks/shared",
                },
            ],
            "screenshots": [
                {
                    "src": "/linkding/static/linkding-screenshot.png",
                    "type": "image/png",
                    "sizes": "2158x1160",
                    "form_factor": "wide",
                }
            ],
            "share_target": {
                "action": "/linkding/bookmarks/new",
                "method": "GET",
                "enctype": "application/x-www-form-urlencoded",
                "params": {
                    "url": "url",
                    "text": "url",
                    "title": "title",
                },
            },
        }
        self.assertDictEqual(response_body, expected_body)
