from unittest.mock import patch

from django.db import connections
from django.test import TestCase

from bookmarks.views.settings import app_version


class HealthViewTestCase(TestCase):

    def test_health_healthy(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)

        response_body = response.json()
        expected_body = {"version": app_version, "status": "healthy"}
        self.assertDictEqual(response_body, expected_body)

    def test_health_unhealhty(self):
        with patch.object(
            connections["default"], "ensure_connection"
        ) as mock_ensure_connection:
            mock_ensure_connection.side_effect = Exception("Connection error")

            response = self.client.get("/health")

            self.assertEqual(response.status_code, 500)

            response_body = response.json()
            expected_body = {"version": app_version, "status": "unhealthy"}
            self.assertDictEqual(response_body, expected_body)
