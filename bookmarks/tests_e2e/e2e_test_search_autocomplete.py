import re

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class SearchAutocompleteE2ETestCase(LinkdingE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.setup_bookmark(title="Python tutorial")
        self.setup_bookmark(title="Rust book")

    def locate_search_input(self):
        return self.page.get_by_placeholder("Search for words or #tags")

    def locate_suggestions(self):
        return self.page.locator("ld-search-autocomplete .menu")

    def test_ignores_slow_suggestions_for_previous_query(self):
        page = self.open(reverse("linkding:bookmarks.index"))
        search = self.locate_search_input()
        suggestions = self.locate_suggestions()

        # Hold the suggestions response for the first query
        previous_query = re.compile(r"/api/bookmarks/\?.*q=pyth")
        held_routes = []
        page.route(previous_query, lambda route: held_routes.append(route))

        with page.expect_request(previous_query):
            search.fill("pyth")
        search.fill("rust")
        expect(suggestions).to_contain_text("Rust book")

        # Let the response for the first query arrive after the newer one
        with page.expect_response(previous_query):
            held_routes[0].continue_()
        page.wait_for_timeout(timeout=1000)

        expect(suggestions).to_be_visible()
        expect(suggestions).to_contain_text("Rust book")
        expect(suggestions).not_to_contain_text("Python tutorial")

    def test_escape_does_not_reopen_suggestions(self):
        self.open(reverse("linkding:bookmarks.index"))
        search = self.locate_search_input()
        suggestions = self.locate_suggestions()

        search.fill("rust")
        search.press("Escape")
        self.page.wait_for_timeout(timeout=1000)

        expect(suggestions).not_to_be_visible()

    def test_blur_does_not_reopen_suggestions(self):
        self.open(reverse("linkding:bookmarks.index"))
        search = self.locate_search_input()
        suggestions = self.locate_suggestions()

        search.fill("rust")
        search.blur()
        self.page.wait_for_timeout(timeout=1000)

        expect(suggestions).not_to_be_visible()
