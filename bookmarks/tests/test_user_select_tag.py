from django.db.models import QuerySet
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import BookmarkSearch, User
from bookmarks.tests.helpers import BookmarkFactoryMixin


class UserSelectTagTest(TestCase, BookmarkFactoryMixin):
    def render_template(self, url: str, users: QuerySet[User] = User.objects.all()):
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
                "users": users,
            },
        )
        template_to_render = Template(
            "{% load bookmarks %}" "{% user_select search users %}"
        )
        return template_to_render.render(context)

    def assertUserOption(self, html: str, user: User, selected: bool = False):
        self.assertInHTML(
            f"""
          <option value="{user.username}" {'selected' if selected else ''}>
            {user.username}
          </option>        
        """,
            html,
        )

    def assertHiddenInput(self, html: str, name: str, value: str = None):
        needle = f'<input type="hidden" name="{name}"'
        if value is not None:
            needle += f' value="{value}"'

        self.assertIn(needle, html)

    def assertNoHiddenInput(self, html: str, name: str):
        needle = f'<input type="hidden" name="{name}"'

        self.assertNotIn(needle, html)

    def test_empty_option(self):
        rendered_template = self.render_template("/test")

        self.assertInHTML(
            f"""
          <option value="" selected="">Everyone</option>        
        """,
            rendered_template,
        )

    def test_render_user_options(self):
        user1 = User.objects.create_user("user1", "user1@example.com", "password123")
        user2 = User.objects.create_user("user2", "user2@example.com", "password123")
        user3 = User.objects.create_user("user3", "user3@example.com", "password123")

        rendered_template = self.render_template("/test", User.objects.all())

        self.assertUserOption(rendered_template, user1)
        self.assertUserOption(rendered_template, user2)
        self.assertUserOption(rendered_template, user3)

    def test_preselect_user_option(self):
        user1 = User.objects.create_user("user1", "user1@example.com", "password123")
        User.objects.create_user("user2", "user2@example.com", "password123")
        User.objects.create_user("user3", "user3@example.com", "password123")

        rendered_template = self.render_template("/test?user=user1", User.objects.all())

        self.assertUserOption(rendered_template, user1, True)

    def test_hidden_inputs(self):
        # Without params
        url = "/test"
        rendered_template = self.render_template(url)

        self.assertNoHiddenInput(rendered_template, "user")
        self.assertNoHiddenInput(rendered_template, "q")
        self.assertNoHiddenInput(rendered_template, "sort")
        self.assertNoHiddenInput(rendered_template, "shared")
        self.assertNoHiddenInput(rendered_template, "unread")

        # With params
        url = "/test?q=foo&user=john&sort=title_asc&shared=yes&unread=yes"
        rendered_template = self.render_template(url)

        self.assertNoHiddenInput(rendered_template, "user")
        self.assertHiddenInput(rendered_template, "q", "foo")
        self.assertHiddenInput(rendered_template, "sort", "title_asc")
        self.assertHiddenInput(rendered_template, "shared", "yes")
        self.assertHiddenInput(rendered_template, "unread", "yes")
