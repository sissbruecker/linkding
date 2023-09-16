from django.db.models import QuerySet
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import BookmarkSearch, Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkSearchTagTest(TestCase, BookmarkFactoryMixin):
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

    def assertHiddenInput(self, html: str, name: str, value: str = None):
        needle = f'<input type="hidden" name="{name}"'
        if value is not None:
            needle += f' value="{value}"'

        self.assertIn(needle, html)

    def assertNoHiddenInput(self, html: str, name: str):
        needle = f'<input type="hidden" name="{name}"'

        self.assertNotIn(needle, html)

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

    def test_hidden_inputs(self):
        # Without params
        url = '/test'
        rendered_template = self.render_template(url)

        self.assertNoHiddenInput(rendered_template, 'user')
        self.assertNoHiddenInput(rendered_template, 'q')
        self.assertNoHiddenInput(rendered_template, 'sort')
        self.assertNoHiddenInput(rendered_template, 'shared')
        self.assertNoHiddenInput(rendered_template, 'unread')

        # With params
        url = '/test?q=foo&user=john&sort=title_asc&shared=shared&unread=yes'
        rendered_template = self.render_template(url)

        self.assertHiddenInput(rendered_template, 'user', 'john')
        self.assertNoHiddenInput(rendered_template, 'q')
        self.assertNoHiddenInput(rendered_template, 'sort')
        self.assertNoHiddenInput(rendered_template, 'shared')
        self.assertNoHiddenInput(rendered_template, 'unread')

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
        url = '/test?shared=shared'
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
