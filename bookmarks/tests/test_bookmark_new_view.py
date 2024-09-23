from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BookmarkNewViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def create_form_data(self, overrides=None):
        if overrides is None:
            overrides = {}
        form_data = {
            "url": "http://example.com",
            "tag_string": "tag1 tag2",
            "title": "test title",
            "description": "test description",
            "notes": "test notes",
            "unread": False,
            "shared": False,
            "auto_close": "",
        }
        return {**form_data, **overrides}

    def test_should_create_new_bookmark(self):
        form_data = self.create_form_data()

        self.client.post(reverse("bookmarks:new"), form_data)

        self.assertEqual(Bookmark.objects.count(), 1)

        bookmark = Bookmark.objects.first()
        self.assertEqual(bookmark.owner, self.user)
        self.assertEqual(bookmark.url, form_data["url"])
        self.assertEqual(bookmark.title, form_data["title"])
        self.assertEqual(bookmark.description, form_data["description"])
        self.assertEqual(bookmark.notes, form_data["notes"])
        self.assertEqual(bookmark.unread, form_data["unread"])
        self.assertEqual(bookmark.shared, form_data["shared"])
        self.assertEqual(bookmark.tags.count(), 2)
        tags = bookmark.tags.order_by("name").all()
        self.assertEqual(tags[0].name, "tag1")
        self.assertEqual(tags[1].name, "tag2")

    def test_should_return_422_with_invalid_form(self):
        form_data = self.create_form_data({"url": ""})
        response = self.client.post(reverse("bookmarks:new"), form_data)
        self.assertEqual(response.status_code, 422)

    def test_should_create_new_unread_bookmark(self):
        form_data = self.create_form_data({"unread": True})

        self.client.post(reverse("bookmarks:new"), form_data)

        self.assertEqual(Bookmark.objects.count(), 1)

        bookmark = Bookmark.objects.first()
        self.assertTrue(bookmark.unread)

    def test_should_create_new_shared_bookmark(self):
        form_data = self.create_form_data({"shared": True})

        self.client.post(reverse("bookmarks:new"), form_data)

        self.assertEqual(Bookmark.objects.count(), 1)

        bookmark = Bookmark.objects.first()
        self.assertTrue(bookmark.shared)

    def test_should_prefill_url_from_url_parameter(self):
        response = self.client.get(reverse("bookmarks:new") + "?url=http://example.com")
        html = response.content.decode()

        self.assertInHTML(
            '<input type="text" name="url" value="http://example.com" '
            'placeholder=" " autofocus class="form-input" required '
            'id="id_url">',
            html,
        )

    def test_should_prefill_title_from_url_parameter(self):
        response = self.client.get(reverse("bookmarks:new") + "?title=Example%20Title")
        html = response.content.decode()

        self.assertInHTML(
            '<input type="text" name="title" value="Example Title" '
            'class="form-input" maxlength="512" autocomplete="off" '
            'id="id_title">',
            html,
        )

    def test_should_prefill_description_from_url_parameter(self):
        response = self.client.get(
            reverse("bookmarks:new") + "?description=Example%20Site%20Description"
        )
        html = response.content.decode()

        self.assertInHTML(
            '<textarea name="description" class="form-input" cols="40" '
            'rows="3" id="id_description">Example Site Description</textarea>',
            html,
        )

    def test_should_prefill_notes_from_url_parameter(self):
        response = self.client.get(
            reverse("bookmarks:new")
            + "?notes=%2A%2AFind%2A%2A%20more%20info%20%5Bhere%5D%28http%3A%2F%2Fexample.com%29"
        )
        html = response.content.decode()

        self.assertInHTML(
            """
            <details class="notes" open="">
                <summary>
                    <span class="form-label d-inline-block">Notes</span>
                </summary>
                <label for="id_notes" class="text-assistive">Notes</label>
                <textarea name="notes" cols="40" rows="8" class="form-input" id="id_notes">**Find** more info [here](http://example.com)</textarea>
                <div class="form-input-hint">
                    Additional notes, supports Markdown.
                </div>
            </details>
            """,
            html,
        )

    def test_should_enable_auto_close_when_specified_in_url_parameter(self):
        response = self.client.get(reverse("bookmarks:new") + "?auto_close")
        html = response.content.decode()

        self.assertInHTML(
            '<input type="hidden" name="auto_close" value="true" '
            'id="id_auto_close">',
            html,
        )

    def test_should_not_enable_auto_close_when_not_specified_in_url_parameter(self):
        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()

        self.assertInHTML(
            '<input type="hidden" name="auto_close" id="id_auto_close">', html
        )

    def test_should_redirect_to_index_view(self):
        form_data = self.create_form_data()

        response = self.client.post(reverse("bookmarks:new"), form_data)

        self.assertRedirects(response, reverse("bookmarks:index"))

    def test_should_not_redirect_to_external_url(self):
        form_data = self.create_form_data()

        response = self.client.post(
            reverse("bookmarks:new") + "?return_url=https://example.com", form_data
        )

        self.assertRedirects(response, reverse("bookmarks:index"))

    def test_auto_close_should_redirect_to_close_view(self):
        form_data = self.create_form_data({"auto_close": "true"})

        response = self.client.post(reverse("bookmarks:new"), form_data)

        self.assertRedirects(response, reverse("bookmarks:close"))

    def test_should_respect_share_profile_setting(self):
        self.user.profile.enable_sharing = False
        self.user.profile.save()
        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <label for="id_shared" class="form-checkbox">
              <input type="checkbox" name="shared" id="id_shared">
              <i class="form-icon"></i>
              <span>Share</span>
            </label>            
        """,
            html,
            count=0,
        )

        self.user.profile.enable_sharing = True
        self.user.profile.save()
        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <label for="id_shared" class="form-checkbox">
              <input type="checkbox" name="shared" id="id_shared">
              <i class="form-icon"></i>
              <span>Share</span>
            </label>            
        """,
            html,
            count=1,
        )

    def test_should_show_respective_share_hint(self):
        self.user.profile.enable_sharing = True
        self.user.profile.save()

        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()
        self.assertInHTML(
            """
          <div class="form-input-hint">
              Share this bookmark with other registered users.
          </div>
        """,
            html,
        )

        self.user.profile.enable_public_sharing = True
        self.user.profile.save()

        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()
        self.assertInHTML(
            """
          <div class="form-input-hint">
              Share this bookmark with other registered users and anonymous users.
          </div>
        """,
            html,
        )

    def test_should_hide_notes_if_there_are_no_notes(self):
        bookmark = self.setup_bookmark()
        response = self.client.get(reverse("bookmarks:edit", args=[bookmark.id]))

        self.assertContains(response, '<details class="notes">', count=1)

    def test_should_not_check_unread_by_default(self):
        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()

        self.assertInHTML(
            '<input type="checkbox" name="unread" id="id_unread">',
            html,
        )

    def test_should_check_unread_when_configured_in_profile(self):
        self.user.profile.default_mark_unread = True
        self.user.profile.save()

        response = self.client.get(reverse("bookmarks:new"))
        html = response.content.decode()

        self.assertInHTML(
            '<input type="checkbox" name="unread" value="true" '
            'id="id_unread" checked="">',
            html,
        )
