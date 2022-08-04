from django.db.models import QuerySet
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import BookmarkFilters, User
from bookmarks.tests.helpers import BookmarkFactoryMixin


class UserSelectTagTest(TestCase, BookmarkFactoryMixin):
    def render_template(self, url: str, users: QuerySet[User] = User.objects.all()):
        rf = RequestFactory()
        request = rf.get(url)
        filters = BookmarkFilters(request)
        context = RequestContext(request, {
            'request': request,
            'filters': filters,
            'users': users,
        })
        template_to_render = Template(
            '{% load bookmarks %}'
            '{% user_select filters users %}'
        )
        return template_to_render.render(context)

    def assertUserOption(self, html: str, user: User, selected: bool = False):
        self.assertInHTML(f'''
          <option value="{user.username}"
                  {'selected' if selected else ''}
                  data-is-user-option>
            {user.username}
          </option>        
        ''', html)

    def test_empty_option(self):
        rendered_template = self.render_template('/test')

        self.assertInHTML(f'''
          <option value="">Everyone</option>        
        ''', rendered_template)

    def test_render_user_options(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')

        rendered_template = self.render_template('/test', User.objects.all())

        self.assertUserOption(rendered_template, user1)
        self.assertUserOption(rendered_template, user2)
        self.assertUserOption(rendered_template, user3)

    def test_preselect_user_option(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        User.objects.create_user('user2', 'user2@example.com', 'password123')
        User.objects.create_user('user3', 'user3@example.com', 'password123')

        rendered_template = self.render_template('/test?user=user1', User.objects.all())

        self.assertUserOption(rendered_template, user1, True)

    def test_render_hidden_inputs_for_filter_params(self):
        # Should render hidden inputs if query param exists
        url = '/test?q=foo&user=john'
        rendered_template = self.render_template(url)

        self.assertInHTML('''
            <input type="hidden" name="q" value="foo">
        ''', rendered_template)

        # Should not render hidden inputs if query param does not exist
        url = '/test?user=john'
        rendered_template = self.render_template(url)

        self.assertInHTML('''
            <input type="hidden" name="q" value="foo">
        ''', rendered_template, count=0)
