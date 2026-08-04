import re
from urllib.parse import parse_qs, urlparse

from django.urls import reverse

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class RandomSortE2ETestCase(LinkdingE2ETestCase):
    def _setup_bookmarks(self, count: int, items_per_page: int):
        profile = self.get_or_create_test_user().profile
        profile.items_per_page = items_per_page
        profile.save()
        self.setup_numbered_bookmarks(count, prefix="bookmark")

    def _bookmark_titles(self):
        return self.page.locator("ul.bookmark-list > li .title a").all_inner_texts()

    def _seed_from_url(self, url: str) -> str:
        return parse_qs(urlparse(url).query).get("random_seed", [None])[0]

    def test_random_sort_redirects_to_url_with_seed(self):
        self._setup_bookmarks(count=3, items_per_page=30)

        page = self.open(reverse("linkding:bookmarks.index") + "?sort=random")

        page.wait_for_url(re.compile(r"random_seed=\d+"))
        seed = self._seed_from_url(page.url)
        self.assertIsNotNone(seed)
        self.assertTrue(seed.isdigit())

    def test_random_sort_pagination_is_stable_and_non_overlapping(self):
        self._setup_bookmarks(count=12, items_per_page=5)

        page = self.open(reverse("linkding:bookmarks.index") + "?sort=random")
        page.wait_for_url(re.compile(r"random_seed=\d+"))
        seed = self._seed_from_url(page.url)

        page_one_titles = self._bookmark_titles()
        self.assertEqual(len(page_one_titles), 5)

        # Navigate to page 2 via the pagination link
        page.locator(".bookmark-pagination").get_by_role("link", name="2").click()
        page.wait_for_url(re.compile(r"page=2"))

        # Seed must survive the navigation
        self.assertEqual(self._seed_from_url(page.url), seed)

        page_two_titles = self._bookmark_titles()
        self.assertEqual(len(page_two_titles), 5)

        # Pages must not share any bookmarks
        self.assertEqual(set(page_one_titles) & set(page_two_titles), set())

        # Re-opening page 1 with the same seed must reproduce the same ordering
        self.open(
            reverse("linkding:bookmarks.index")
            + f"?sort=random&random_seed={seed}"
        )
        self.assertEqual(self._bookmark_titles(), page_one_titles)
