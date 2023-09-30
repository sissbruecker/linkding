from bs4 import BeautifulSoup
from django.db.models import QuerySet
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import BookmarkSearch, Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class BookmarkSearchTagTest(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def render_template(self, url: str, tags: QuerySet[Tag] = Tag.objects.all()):
        rf = RequestFactory()
        request = rf.get(url)
        request.user = self.get_or_create_test_user()
        request.user_profile = self.get_or_create_test_user().profile
        search = BookmarkSearch.from_request(request)
        context = RequestContext(request, {
            'request': request,
            'search': search,
            'tags': tags,
        })
        template_to_render = Template(
            '{% load bookmarks %}'
            '{% bookmark_search search tags %}'
        )
        return template_to_render.render(context)

    def assertHiddenInput(self, form: BeautifulSoup, name: str, value: str = None):
        input = form.select_one(f'input[name="{name}"][type="hidden"]')
        self.assertIsNotNone(input)

        if value is not None:
            self.assertEqual(input['value'], value)

    def assertNoHiddenInput(self, form: BeautifulSoup, name: str):
        input = form.select_one(f'input[name="{name}"][type="hidden"]')
        self.assertIsNone(input)

    def assertSearchInput(self, form: BeautifulSoup, name: str, value: str = None):
        input = form.select_one(f'input[name="{name}"][type="search"]')
        self.assertIsNotNone(input)

        if value is not None:
            self.assertEqual(input['value'], value)

    def assertSelect(self, form: BeautifulSoup, name: str, value: str = None):
        select = form.select_one(f'select[name="{name}"]')
        self.assertIsNotNone(select)

        if value is not None:
            options = select.select('option')
            for option in options:
                if option['value'] == value:
                    self.assertTrue(option.has_attr('selected'))
                else:
                    self.assertFalse(option.has_attr('selected'))

    def assertRadioGroup(self, form: BeautifulSoup, name: str, value: str = None):
        radios = form.select(f'input[name="{name}"][type="radio"]')
        self.assertTrue(len(radios) > 0)

        if value is not None:
            for radio in radios:
                if radio['value'] == value:
                    self.assertTrue(radio.has_attr('checked'))
                else:
                    self.assertFalse(radio.has_attr('checked'))

    def assertUnmodifiedLabel(self, html: str, text: str, id: str = ''):
        id_attr = f'for="{id}"' if id else ''
        tag = 'label' if id else 'div'
        needle = f'<{tag} class="form-label" {id_attr}>{text}</{tag}>'

        self.assertInHTML(needle, html)

    def assertModifiedLabel(self, html: str, text: str, id: str = ''):
        id_attr = f'for="{id}"' if id else ''
        tag = 'label' if id else 'div'
        needle = f'<{tag} class="form-label text-bold" {id_attr}>{text}</{tag}>'

        self.assertInHTML(needle, html)

    def test_search_form_inputs(self):
        # Without params
        url = '/test'
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        search_form = soup.select_one('form#search')

        self.assertSearchInput(search_form, 'q')
        self.assertNoHiddenInput(search_form, 'user')
        self.assertNoHiddenInput(search_form, 'sort')
        self.assertNoHiddenInput(search_form, 'shared')
        self.assertNoHiddenInput(search_form, 'unread')

        # With params
        url = '/test?q=foo&user=john&sort=title_asc&shared=yes&unread=yes'
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        search_form = soup.select_one('form#search')

        self.assertSearchInput(search_form, 'q', 'foo')
        self.assertHiddenInput(search_form, 'user', 'john')
        self.assertHiddenInput(search_form, 'sort', 'title_asc')
        self.assertHiddenInput(search_form, 'shared', 'yes')
        self.assertHiddenInput(search_form, 'unread', 'yes')

    def test_preferences_form_inputs(self):
        # Without params
        url = '/test'
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        preferences_form = soup.select_one('form#search_preferences')

        self.assertNoHiddenInput(preferences_form, 'q')
        self.assertNoHiddenInput(preferences_form, 'user')
        self.assertNoHiddenInput(preferences_form, 'sort')
        self.assertNoHiddenInput(preferences_form, 'shared')
        self.assertNoHiddenInput(preferences_form, 'unread')

        self.assertSelect(preferences_form, 'sort', 'added_desc')
        self.assertRadioGroup(preferences_form, 'shared', '')
        self.assertRadioGroup(preferences_form, 'unread', '')

        # With params
        url = '/test?q=foo&user=john&sort=title_asc&shared=yes&unread=yes'
        rendered_template = self.render_template(url)
        soup = self.make_soup(rendered_template)
        preferences_form = soup.select_one('form#search_preferences')

        self.assertHiddenInput(preferences_form, 'q', 'foo')
        self.assertHiddenInput(preferences_form, 'user', 'john')
        self.assertNoHiddenInput(preferences_form, 'sort')
        self.assertNoHiddenInput(preferences_form, 'shared')
        self.assertNoHiddenInput(preferences_form, 'unread')

        self.assertSelect(preferences_form, 'sort', 'title_asc')
        self.assertRadioGroup(preferences_form, 'shared', 'yes')
        self.assertRadioGroup(preferences_form, 'unread', 'yes')

    def test_modified_indicator(self):
        # Without modifications
        url = '/test'
        rendered_template = self.render_template(url)

        self.assertIn('<button type="button" class="btn dropdown-toggle ">', rendered_template)

        # With modifications
        url = '/test?sort=title_asc'
        rendered_template = self.render_template(url)

        self.assertIn('<button type="button" class="btn dropdown-toggle badge">', rendered_template)

    def test_modified_labels(self):
        # Without modifications
        url = '/test'
        rendered_template = self.render_template(url)

        self.assertUnmodifiedLabel(rendered_template, 'Sort by', 'id_sort')
        self.assertUnmodifiedLabel(rendered_template, 'Shared filter')
        self.assertUnmodifiedLabel(rendered_template, 'Unread filter')

        # Modified sort
        url = '/test?sort=title_asc'
        rendered_template = self.render_template(url)
        self.assertModifiedLabel(rendered_template, 'Sort by', 'id_sort')
        self.assertUnmodifiedLabel(rendered_template, 'Shared filter')
        self.assertUnmodifiedLabel(rendered_template, 'Unread filter')

        # Modified shared
        url = '/test?shared=yes'
        rendered_template = self.render_template(url)
        self.assertUnmodifiedLabel(rendered_template, 'Sort by', 'id_sort')
        self.assertModifiedLabel(rendered_template, 'Shared filter')
        self.assertUnmodifiedLabel(rendered_template, 'Unread filter')

        # Modified unread
        url = '/test?unread=yes'
        rendered_template = self.render_template(url)
        self.assertUnmodifiedLabel(rendered_template, 'Sort by', 'id_sort')
        self.assertUnmodifiedLabel(rendered_template, 'Shared filter')
        self.assertModifiedLabel(rendered_template, 'Unread filter')
