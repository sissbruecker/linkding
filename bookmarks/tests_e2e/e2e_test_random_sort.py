import re
from urllib.parse import parse_qs, urlparse

from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class RandomSortE2ETestCase(LinkdingE2ETestCase):
    def setup_fixture(self, count: int, items_per_page: int):
        profile = self.get_or_create_test_user().profile
        profile.items_per_page = items_per_page
        profile.save()
        self.setup_numbered_bookmarks(count)

    def locate_titles(self):
        return self.page.locator("ul.bookmark-list > li .title a")

    def get_seed(self) -> str:
        return parse_qs(urlparse(self.page.url).query)["random_seed"][0]

    def test_random_sort_redirects_to_url_with_seed(self):
        self.setup_fixture(count=3, items_per_page=30)

        self.open(reverse("linkding:bookmarks.index") + "?sort=random")

        expect(self.page).to_have_url(re.compile(r"random_seed=\d+"))

    def test_random_sort_pagination_is_stable_and_non_overlapping(self):
        self.setup_fixture(count=12, items_per_page=5)

        self.open(reverse("linkding:bookmarks.index") + "?sort=random")
        expect(self.page).to_have_url(re.compile(r"random_seed=\d+"))
        seed = self.get_seed()

        expect(self.locate_titles()).to_have_count(5)
        page_one_titles = self.locate_titles().all_inner_texts()

        self.page.locator(".bookmark-pagination").get_by_role("link", name="2").click()
        expect(self.page).to_have_url(re.compile(r"page=2"))
        self.assertEqual(self.get_seed(), seed)

        expect(self.locate_titles()).not_to_have_text(page_one_titles)
        expect(self.locate_titles()).to_have_count(5)
        page_two_titles = self.locate_titles().all_inner_texts()
        self.assertEqual(set(page_one_titles) & set(page_two_titles), set())

        self.open(
            reverse("linkding:bookmarks.index") + f"?sort=random&random_seed={seed}"
        )
        expect(self.locate_titles()).to_have_text(page_one_titles)
