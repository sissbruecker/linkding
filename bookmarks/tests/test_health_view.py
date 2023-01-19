from django.test import TestCase
from bookmarks.views.settings import app_version

class HealthViewTestCase(TestCase):
    
    def test_health_endpoint_success(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)

        responseBody = response.json()
        expectedBody = {
            'version': app_version,
            'status': 'healthy'
        }
        self.assertDictEqual(responseBody, expectedBody)