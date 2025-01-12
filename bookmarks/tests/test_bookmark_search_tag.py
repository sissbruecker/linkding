from bs4 import BeautifulSoup
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import BookmarkSearch
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BookmarkSearchTagTest(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def render_template(self, url: str, mode: str = ""):
        rf = RequestFactory()
        request = rf.get(url)
        request.user = self.get_or_create_test_user()
        request.user_profile = self.get_or_create_test_user().profile
        search = BookmarkSearch.from_request(request.GET)
        context = RequestContext(
            request,
            {
                "request": request,
                "search": search,
                "mode": mode,
            },
        )
        template_to_render = Template(
            "{% load bookmarks %} {% bookmark_search search mode %}"
        )
        return template_to_render.render(context)

    def assertHiddenInput(self, form: BeautifulSoup, name: str, value: str = None):
        element = form.select_one(f'input[name="{name}"][type="hidden"]')
        self.assertIsNotNone(element)

        if value is not None:
            self.assertEqual(element["value"], value)

    def assertNoHiddenInput(self, form: BeautifulSoup, name: str):
        element = form.select_one(f'input[name="{name}"][type="hidden"]')
        self.assertIsNone(element)

    def assertSearchInput(self, form: BeautifulSoup, name: str, value: str = None):
        element = form.select_one(f'input[name="{name}"][type="search"]')
        self.assertIsNotNone(element)

        if value is not None:
            self.assertEqual(element["value"], value)

    def assertSelect(self, form: BeautifulSoup, name: str, value: str = None):
        select = form.select_one(f'select[name="{name}"]')
        self.assertIsNotNone(select)

        if value is not None:
            options = select.select("option")
            for option in options:
                if option["value"] == value:
                    self.assertTrue(option.has_attr("selected"))
                else:
                    self.assertFalse(option.has_attr("selected"))

    def assertRadioGroup(self, form: BeautifulSoup, name: str, value: str = None):
        radios = form.select(f'input[name="{name}"][type="radio"]')
        self.assertTrue(len(radios) > 0)

        if value is not None:
            for radio in radios:
                if radio["value"] == value:
                    self.assertTrue(radio.has_attr("checked"))
                else:
                    self.assertFalse(radio.has_attr("checked"))

    def assertNoRadioGroup(self, form: BeautifulSoup, name: str):
        radios = form.select(f'input[name="{name}"][type="radio"]')
        self.assertTrue(len(radios) == 0)

    def assertUnmodifiedLabel(self, html: str, text: str):
        soup = self.make_soup(html)
        label = soup.find("label", string=lambda s: s and s.strip() == text)
        self.assertEqual(label["class"], ["form-label"])

    def assertModifiedLabel(self, html: str, text: str):
        soup = self.make_soup(html)
        label = soup.find("label", string=lambda s: s and s.strip() == text)
        self.assertEqual(label["class"], ["form-label", "text-bold"])

    def test_search_form_inputs(self):
        # Without params
        url = "/test"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        search_form = soup.select_one("form#search")

        self.assertSearchInput(search_form, "q")
        self.assertNoHiddenInput(search_form, "user")
        self.assertNoHiddenInput(search_form, "sort")
        self.assertNoHiddenInput(search_form, "shared")
        self.assertNoHiddenInput(search_form, "unread")

        # With params
        url = "/test?q=foo&user=john&sort=title_asc&shared=yes&unread=yes"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        search_form = soup.select_one("form#search")

        self.assertSearchInput(search_form, "q", "foo")
        self.assertHiddenInput(search_form, "user", "john")
        self.assertHiddenInput(search_form, "sort", BookmarkSearch.SORT_TITLE_ASC)
        self.assertHiddenInput(
            search_form, "shared", BookmarkSearch.FILTER_SHARED_SHARED
        )
        self.assertHiddenInput(search_form, "unread", BookmarkSearch.FILTER_UNREAD_YES)

    def test_preferences_form_inputs(self):
        # Without params
        url = "/test"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        preferences_form = soup.select_one("form#search_preferences")

        self.assertNoHiddenInput(preferences_form, "q")
        self.assertNoHiddenInput(preferences_form, "user")
        self.assertNoHiddenInput(preferences_form, "sort")
        self.assertNoHiddenInput(preferences_form, "shared")
        self.assertNoHiddenInput(preferences_form, "unread")

        self.assertSelect(preferences_form, "sort", BookmarkSearch.SORT_ADDED_DESC)
        self.assertRadioGroup(
            preferences_form, "shared", BookmarkSearch.FILTER_SHARED_OFF
        )
        self.assertRadioGroup(
            preferences_form, "unread", BookmarkSearch.FILTER_UNREAD_OFF
        )

        # With params
        url = "/test?q=foo&user=john&sort=title_asc&shared=yes&unread=yes"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        preferences_form = soup.select_one("form#search_preferences")

        self.assertHiddenInput(preferences_form, "q", "foo")
        self.assertHiddenInput(preferences_form, "user", "john")
        self.assertNoHiddenInput(preferences_form, "sort")
        self.assertNoHiddenInput(preferences_form, "shared")
        self.assertNoHiddenInput(preferences_form, "unread")

        self.assertSelect(preferences_form, "sort", BookmarkSearch.SORT_TITLE_ASC)
        self.assertRadioGroup(
            preferences_form, "shared", BookmarkSearch.FILTER_SHARED_SHARED
        )
        self.assertRadioGroup(
            preferences_form, "unread", BookmarkSearch.FILTER_UNREAD_YES
        )

    def test_preferences_form_inputs_shared_mode(self):
        # Without params
        url = "/test"
        rendered_template = self.render_template(url, mode="shared")
        soup = self.make_soup(rendered_template)
        preferences_form = soup.select_one("form#search_preferences")

        self.assertNoHiddenInput(preferences_form, "q")
        self.assertNoHiddenInput(preferences_form, "user")
        self.assertNoHiddenInput(preferences_form, "sort")
        self.assertNoHiddenInput(preferences_form, "shared")
        self.assertNoHiddenInput(preferences_form, "unread")

        self.assertSelect(preferences_form, "sort", BookmarkSearch.SORT_ADDED_DESC)
        self.assertNoRadioGroup(preferences_form, "shared")
        self.assertNoRadioGroup(preferences_form, "unread")

        # With params
        url = "/test?q=foo&user=john&sort=title_asc"
        rendered_template = self.render_template(url, mode="shared")
        soup = self.make_soup(rendered_template)
        preferences_form = soup.select_one("form#search_preferences")

        self.assertHiddenInput(preferences_form, "q", "foo")
        self.assertHiddenInput(preferences_form, "user", "john")
        self.assertNoHiddenInput(preferences_form, "sort")
        self.assertNoHiddenInput(preferences_form, "shared")
        self.assertNoHiddenInput(preferences_form, "unread")

        self.assertSelect(preferences_form, "sort", BookmarkSearch.SORT_TITLE_ASC)
        self.assertNoRadioGroup(preferences_form, "shared")
        self.assertNoRadioGroup(preferences_form, "unread")

    def test_modified_indicator(self):
        # Without modifications
        url = "/test"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        button = soup.select_one("button[aria-label='Search preferences']")

        self.assertNotIn("badge", button["class"])

        # With modifications
        url = "/test?sort=title_asc"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        button = soup.select_one("button[aria-label='Search preferences']")

        self.assertIn("badge", button["class"])

        # Ignores non-preferences modifications
        url = "/test?q=foo&user=john"
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        button = soup.select_one("button[aria-label='Search preferences']")

        self.assertNotIn("badge", button["class"])

    def test_modified_labels(self):
        # Without modifications
        url = "/test"
        rendered_template = self.render_template(url)

        self.assertUnmodifiedLabel(rendered_template, "Sort by")
        self.assertUnmodifiedLabel(rendered_template, "Shared filter")
        self.assertUnmodifiedLabel(rendered_template, "Unread filter")

        # Modified sort
        url = "/test?sort=title_asc"
        rendered_template = self.render_template(url)
        self.assertModifiedLabel(rendered_template, "Sort by")
        self.assertUnmodifiedLabel(rendered_template, "Shared filter")
        self.assertUnmodifiedLabel(rendered_template, "Unread filter")

        # Modified shared
        url = "/test?shared=yes"
        rendered_template = self.render_template(url)
        self.assertUnmodifiedLabel(rendered_template, "Sort by")
        self.assertModifiedLabel(rendered_template, "Shared filter")
        self.assertUnmodifiedLabel(rendered_template, "Unread filter")

        # Modified unread
        url = "/test?unread=yes"
        rendered_template = self.render_template(url)
        self.assertUnmodifiedLabel(rendered_template, "Sort by")
        self.assertUnmodifiedLabel(rendered_template, "Shared filter")
        self.assertModifiedLabel(rendered_template, "Unread filter")
