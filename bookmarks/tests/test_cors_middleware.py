from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.test import override_settings
from django.urls import reverse

from bookmarks.middlewares import CorsMiddleware
from bookmarks.tests.helpers import BookmarkFactoryMixin, LinkdingApiTestCase

ORIGIN = "https://frontend.example.com"
OTHER_ORIGIN = "https://other.example.com"
INVALID_ORIGINS = [
    "frontend.example.com",
    "null",
    "https://frontend.example.com/path",
    "https://frontend.example.com?query=1",
    "https://frontend.example.com#fragment",
    "https://user:password@frontend.example.com",
    "https://user@frontend.example.com",
    "*",
]


def cors_origins(*origins):
    return override_settings(LD_CORS_ALLOWED_ORIGINS=",".join(origins))


class CorsMiddlewareTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.api_url = reverse("linkding:bookmark-list")

    def assertNoCorsHeaders(self, response):
        self.assertNotIn("Access-Control-Allow-Origin", response)
        self.assertNotIn("Access-Control-Allow-Methods", response)
        self.assertNotIn("Access-Control-Allow-Headers", response)
        self.assertNotIn("Access-Control-Max-Age", response)

    def preflight(self, url, origin=ORIGIN):
        return self.client.options(
            url,
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )

    def assertMiddlewareNotUsed(self):
        with self.assertRaises(MiddlewareNotUsed):
            CorsMiddleware(lambda request: None)

    def test_disabled_by_default(self):
        self.assertEqual(settings.LD_CORS_ALLOWED_ORIGINS, "")
        self.assertMiddlewareNotUsed()

        # Preflight is not answered by the middleware, but reaches the API view
        response = self.preflight(self.api_url)
        self.assertEqual(response.status_code, 401)
        self.assertNoCorsHeaders(response)

    @cors_origins("", "  ")
    def test_disabled_for_empty_origins(self):
        self.assertMiddlewareNotUsed()

    @cors_origins(*INVALID_ORIGINS)
    def test_disabled_for_invalid_origins(self):
        self.assertMiddlewareNotUsed()

    @cors_origins(ORIGIN, OTHER_ORIGIN)
    def test_allowed_origins(self):
        self.authenticate()

        for origin in [ORIGIN, OTHER_ORIGIN]:
            response = self.client.get(self.api_url, headers={"Origin": origin})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Access-Control-Allow-Origin"], origin)
            self.assertIn("Origin", response["Vary"])
            self.assertNotIn("Access-Control-Allow-Methods", response)
            self.assertNotIn("Access-Control-Allow-Credentials", response)

    @cors_origins(ORIGIN)
    def test_rejected_origins(self):
        self.authenticate()

        for origin in [
            OTHER_ORIGIN,
            "http://frontend.example.com",
            "https://frontend.example.com:8443",
            "https://frontend.example.com/path",
            "null",
        ]:
            response = self.client.get(self.api_url, headers={"Origin": origin})

            self.assertEqual(response.status_code, 200)
            self.assertNoCorsHeaders(response)
            self.assertIn("Origin", response["Vary"])

        response = self.client.get(self.api_url)

        self.assertEqual(response.status_code, 200)
        self.assertNoCorsHeaders(response)

    @cors_origins(*INVALID_ORIGINS, ORIGIN)
    def test_invalid_origins_are_ignored(self):
        self.authenticate()

        with self.assertLogs("bookmarks.middlewares", level="WARNING") as logs:
            response = self.client.get(self.api_url, headers={"Origin": ORIGIN})

        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

        messages = [record.getMessage() for record in logs.records]
        self.assertEqual(len(messages), len(INVALID_ORIGINS))
        for origin, message in zip(INVALID_ORIGINS, messages, strict=True):
            self.assertIn("Ignoring invalid origin in LD_CORS_ALLOWED_ORIGINS", message)
            self.assertIn(f"'{origin}'", message)

        for origin in INVALID_ORIGINS + [OTHER_ORIGIN]:
            response = self.client.get(self.api_url, headers={"Origin": origin})
            self.assertNoCorsHeaders(response)

    @cors_origins(" " + ORIGIN + " ", "", "  ")
    def test_trims_whitespace_and_ignores_empty_entries(self):
        self.authenticate()

        with self.assertNoLogs("bookmarks.middlewares", level="WARNING"):
            response = self.client.get(self.api_url, headers={"Origin": ORIGIN})

        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

    @cors_origins(ORIGIN + "/")
    def test_allows_trailing_slash_in_configured_origin(self):
        self.authenticate()

        response = self.client.get(self.api_url, headers={"Origin": ORIGIN})

        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

    @cors_origins(ORIGIN)
    def test_preflight_does_not_require_authentication(self):
        response = self.preflight(self.api_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)
        self.assertEqual(
            response["Access-Control-Allow-Methods"],
            "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        )
        self.assertEqual(
            response["Access-Control-Allow-Headers"], "Authorization, Content-Type"
        )
        self.assertEqual(response["Access-Control-Max-Age"], "86400")
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    @cors_origins(ORIGIN)
    def test_preflight_from_unknown_origin(self):
        response = self.preflight(self.api_url, origin=OTHER_ORIGIN)

        self.assertEqual(response.status_code, 200)
        self.assertNoCorsHeaders(response)

    @cors_origins(ORIGIN)
    def test_plain_options_request_is_passed_to_view(self):
        response = self.client.options(self.api_url, headers={"Origin": ORIGIN})

        # Without Access-Control-Request-Method this is not a preflight, so the
        # API view handles it and rejects the unauthenticated request
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

    @cors_origins(ORIGIN)
    def test_error_responses_include_cors_headers(self):
        response = self.client.get(self.api_url, headers={"Origin": ORIGIN})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

        self.authenticate()
        url = reverse("linkding:bookmark-detail", args=[9999])
        response = self.client.get(url, headers={"Origin": ORIGIN})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

    @cors_origins(ORIGIN)
    def test_non_api_paths_are_not_affected(self):
        response = self.client.get(reverse("login"), headers={"Origin": ORIGIN})

        self.assertNoCorsHeaders(response)
        self.assertNotIn("Origin", response.get("Vary", ""))

        response = self.preflight(reverse("login"))

        self.assertNoCorsHeaders(response)

    @override_settings(LD_CORS_ALLOWED_ORIGINS=ORIGIN, LD_CONTEXT_PATH="linkding/")
    def test_respects_context_path(self):
        response = self.preflight("/linkding/api/bookmarks/")

        self.assertEqual(response["Access-Control-Allow-Origin"], ORIGIN)

        response = self.preflight("/api/bookmarks/")

        self.assertNoCorsHeaders(response)
