from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory
from django.utils import timezone, formats

from bookmarks.models import UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkListTagTest(TestCase, BookmarkFactoryMixin):

    def render_template(self, bookmarks) -> str:
        rf = RequestFactory()
        request = rf.get('/test')
        request.user = self.get_or_create_test_user()
        paginator = Paginator(bookmarks, 10)
        page = paginator.page(1)

        context = RequestContext(request, {'bookmarks': page, 'return_url': '/test'})
        template_to_render = Template(
            '{% load bookmarks %}'
            '{% bookmark_list bookmarks return_url %}'
        )
        return template_to_render.render(context)

    def setup_date_format_test(self, date_display_setting):
        bookmark = self.setup_bookmark()
        bookmark.date_added = timezone.now() - relativedelta(days=8)
        bookmark.save()
        user = self.get_or_create_test_user()
        user.profile.bookmark_date_display = date_display_setting
        user.profile.save()
        return bookmark

    def test_should_respect_absolute_date_setting(self):
        bookmark = self.setup_date_format_test(UserProfile.BOOKMARK_DATE_DISPLAY_ABSOLUTE)
        html = self.render_template([bookmark])
        formatted_date = formats.date_format(bookmark.date_added, 'SHORT_DATE_FORMAT')

        self.assertInHTML(f'''
        <span class="text-gray text-sm">{formatted_date}</span>
        ''', html)

    def test_should_respect_relative_date_setting(self):
        bookmark = self.setup_date_format_test(UserProfile.BOOKMARK_DATE_DISPLAY_RELATIVE)
        html = self.render_template([bookmark])

        self.assertInHTML('''
        <span class="text-gray text-sm">1 week ago</span>
        ''', html)
