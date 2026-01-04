from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.models import UserProfile
from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class SettingsGeneralE2ETestCase(LinkdingE2ETestCase):
    def test_should_only_enable_public_sharing_if_sharing_is_enabled(self):
        self.open(reverse("linkding:settings.general"))

        enable_sharing = self.page.get_by_label("Enable bookmark sharing")
        enable_sharing_label = self.page.get_by_text("Enable bookmark sharing")
        enable_public_sharing = self.page.get_by_label("Enable public bookmark sharing")
        enable_public_sharing_label = self.page.get_by_text(
            "Enable public bookmark sharing"
        )
        default_mark_shared = self.page.get_by_label(
            "Create bookmarks as shared by default"
        )
        default_mark_shared_label = self.page.get_by_text(
            "Create bookmarks as shared by default"
        )

        # Public sharing and default shared are disabled by default
        expect(enable_sharing).not_to_be_checked()
        expect(enable_public_sharing).not_to_be_checked()
        expect(enable_public_sharing).to_be_disabled()
        expect(default_mark_shared).not_to_be_checked()
        expect(default_mark_shared).to_be_disabled()

        # Enable sharing
        enable_sharing_label.click()
        expect(enable_sharing).to_be_checked()
        expect(enable_public_sharing).not_to_be_checked()
        expect(enable_public_sharing).to_be_enabled()
        expect(default_mark_shared).not_to_be_checked()
        expect(default_mark_shared).to_be_enabled()

        # Enable public sharing and default shared
        enable_public_sharing_label.click()
        default_mark_shared_label.click()
        expect(enable_public_sharing).to_be_checked()
        expect(enable_public_sharing).to_be_enabled()
        expect(default_mark_shared).to_be_checked()
        expect(default_mark_shared).to_be_enabled()

        # Disable sharing
        enable_sharing_label.click()
        expect(enable_sharing).not_to_be_checked()
        expect(enable_public_sharing).not_to_be_checked()
        expect(enable_public_sharing).to_be_disabled()
        expect(default_mark_shared).not_to_be_checked()
        expect(default_mark_shared).to_be_disabled()

    def test_should_not_show_bookmark_description_max_lines_when_display_inline(self):
        profile = self.get_or_create_test_user().profile
        profile.bookmark_description_display = (
            UserProfile.BOOKMARK_DESCRIPTION_DISPLAY_INLINE
        )
        profile.save()

        self.open(reverse("linkding:settings.general"))

        max_lines = self.page.get_by_label("Bookmark description max lines")
        expect(max_lines).to_be_hidden()

    def test_should_show_bookmark_description_max_lines_when_display_separate(self):
        profile = self.get_or_create_test_user().profile
        profile.bookmark_description_display = (
            UserProfile.BOOKMARK_DESCRIPTION_DISPLAY_SEPARATE
        )
        profile.save()

        self.open(reverse("linkding:settings.general"))

        max_lines = self.page.get_by_label("Bookmark description max lines")
        expect(max_lines).to_be_visible()

    def test_should_update_bookmark_description_max_lines_when_changing_display(self):
        self.open(reverse("linkding:settings.general"))

        max_lines = self.page.get_by_label("Bookmark description max lines")
        expect(max_lines).to_be_hidden()

        display = self.page.get_by_label("Bookmark description", exact=True)
        display.select_option("separate")
        expect(max_lines).to_be_visible()

        display.select_option("inline")
        expect(max_lines).to_be_hidden()
