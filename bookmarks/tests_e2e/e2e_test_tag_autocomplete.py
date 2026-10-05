from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class TagAutocompleteE2ETestCase(LinkdingE2ETestCase):
    def test_mouse_completion_keeps_end_of_long_input_visible(self):
        self.setup_tag(name="completed-tag")
        page = self.open(reverse("linkding:bookmarks.new"))
        page.set_viewport_size({"width": 390, "height": 844})
        tags = page.get_by_label("Tags", exact=True)
        prefix = "first-long-tag-name second-long-tag-name third-long-tag-name "
        tags.fill(prefix + "com")
        tags.press("End")
        suggestion = page.locator("ld-tag-autocomplete .menu-item a")
        expect(suggestion).to_have_text("completed-tag")

        suggestion.click()

        expect(tags).to_have_value(prefix + "completed-tag ")
        expect(tags).to_be_focused()
        self.assertEqual(
            tags.evaluate("input => input.selectionStart"),
            len(prefix + "completed-tag "),
        )
        self.assertGreater(tags.evaluate("input => input.scrollLeft"), 0)

    def test_keyboard_completion_keeps_caret_before_following_tags(self):
        self.setup_tag(name="completed-tag")
        page = self.open(reverse("linkding:bookmarks.new"))
        tags = page.get_by_label("Tags", exact=True)

        for key in ("Enter", "Tab"):
            with self.subTest(key=key):
                tags.fill("first-tag com last-tag")
                tags.evaluate("input => input.setSelectionRange(13, 13)")
                tags.dispatch_event("input")
                expect(page.locator("ld-tag-autocomplete .menu")).to_be_visible()

                tags.press(key)

                expect(tags).to_have_value("first-tag completed-tag  last-tag")
                expect(tags).to_be_focused()
                self.assertEqual(
                    tags.evaluate("input => input.selectionStart"),
                    len("first-tag completed-tag "),
                )
                tags.press_sequentially("next")
                expect(tags).to_have_value("first-tag completed-tag next last-tag")
