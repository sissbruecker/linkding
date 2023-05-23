from django.test import TestCase, override_settings


class MetadataViewTestCase(TestCase):

    def test_default_manifest(self):
        response = self.client.get("/manifest.json")

        self.assertEqual(response.status_code, 200)

        response_body = response.json()
        expected_body = {
            "short_name": "linkding",
            "start_url": "bookmarks",
            "display": "standalone",
            "scope": "/"
        }
        self.assertDictEqual(response_body, expected_body)

    @override_settings(LD_CONTEXT_PATH="linkding/")
    def test_manifest_respects_context_path(self):
        response = self.client.get("/manifest.json")

        self.assertEqual(response.status_code, 200)

        response_body = response.json()
        expected_body = {
            "short_name": "linkding",
            "start_url": "bookmarks",
            "display": "standalone",
            "scope": "/linkding/"
        }
        self.assertDictEqual(response_body, expected_body)
