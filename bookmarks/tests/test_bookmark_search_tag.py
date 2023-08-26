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

    def assertNoHiddenInput(self, html: str, name: str, value: str = None):
        needle = f'<input type="hidden" name="{name}"'
        if value is not None:
            needle += f' value="{value}"'

        self.assertNotIn(needle, html)

    def test_hidden_inputs(self):
        # Without params
        url = '/test'
        rendered_template = self.render_template(url)

        self.assertNoHiddenInput(rendered_template, 'user')
        self.assertNoHiddenInput(rendered_template, 'q')
        self.assertNoHiddenInput(rendered_template, 'sort')

        # With params
        url = '/test?q=foo&user=john&sort=title_asc'
        rendered_template = self.render_template(url)

        self.assertHiddenInput(rendered_template, 'user')
        self.assertNoHiddenInput(rendered_template, 'q', 'foo')
        self.assertHiddenInput(rendered_template, 'sort', 'title_asc')
