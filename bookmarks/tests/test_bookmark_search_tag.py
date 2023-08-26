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

    def test_render_hidden_inputs_for_filter_params(self):
        # Should render hidden inputs if query param exists
        url = '/test?q=foo&user=john'
        rendered_template = self.render_template(url)

        self.assertInHTML('''
            <input type="hidden" name="user" value="john">
        ''', rendered_template)

        # Should not render hidden inputs if query param does not exist
        url = '/test?q=foo'
        rendered_template = self.render_template(url)

        self.assertInHTML('''
            <input type="hidden" name="user" value="john">
        ''', rendered_template, count=0)
