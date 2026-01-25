from django.urls import reverse
from playwright.sync_api import expect

from bookmarks.models import Tag
from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class TagManagementE2ETestCase(LinkdingE2ETestCase):
    def locate_tag_modal(self):
        modal = self.page.locator("ld-modal.tag-edit-modal")
        expect(modal).to_be_visible()
        return modal

    def locate_merge_modal(self):
        modal = self.page.locator("ld-modal").filter(has_text="Merge Tags")
        expect(modal).to_be_visible()
        return modal

    def locate_tag_row(self, name: str):
        return self.page.locator("table.crud-table tbody tr").filter(has_text=name)

    def verify_success_message(self, text: str):
        success_message = self.page.locator(".toast.toast-success")
        expect(success_message).to_be_visible()
        expect(success_message).to_contain_text(text)

    def test_create_tag(self):
        self.open(reverse("linkding:tags.index"))

        # Click the Create Tag button to open the modal
        self.page.get_by_text("Create Tag").click()

        modal = self.locate_tag_modal()

        # Fill in a tag name
        name_input = modal.get_by_label("Name")
        name_input.fill("test-tag")

        # Submit the form
        modal.get_by_text("Save").click()

        # Verify modal is closed and we're back on the tags page
        expect(modal).not_to_be_visible()

        # Verify the success message is shown
        self.verify_success_message('Tag "test-tag" created successfully.')

        # Verify the new tag is shown in the list
        tag_row = self.locate_tag_row("test-tag")
        expect(tag_row).to_be_visible()

        # Verify the tag was actually created in the database
        self.assertEqual(
            Tag.objects.filter(owner=self.get_or_create_test_user()).count(), 1
        )
        tag = Tag.objects.get(owner=self.get_or_create_test_user())
        self.assertEqual(tag.name, "test-tag")

    def test_create_tag_validation_error(self):
        existing_tag = self.setup_tag(name="existing-tag")

        self.open(reverse("linkding:tags.index"))

        # Click the Create Tag button to open the modal
        self.page.get_by_text("Create Tag").click()

        modal = self.locate_tag_modal()

        # Submit with empty value
        modal.get_by_text("Save").click()

        # Verify the error is shown (field is required)
        error_hint = modal.get_by_text("This field is required")
        expect(error_hint).to_be_visible()

        # Fill in the name of an existing tag
        name_input = modal.get_by_label("Name")
        name_input.fill(existing_tag.name)

        # Submit the form
        modal.get_by_text("Save").click()

        # Verify the error is shown (tag already exists)
        error_hint = modal.get_by_text('Tag "existing-tag" already exists')
        expect(error_hint).to_be_visible()

        # Verify no additional tag was created
        self.assertEqual(
            Tag.objects.filter(owner=self.get_or_create_test_user()).count(), 1
        )

    def test_edit_tag(self):
        tag = self.setup_tag(name="old-name")

        self.open(reverse("linkding:tags.index"))

        # Click the Edit button for the tag
        tag_row = self.locate_tag_row(tag.name)
        tag_row.get_by_role("link", name="Edit").click()

        modal = self.locate_tag_modal()

        # Verify the form is pre-filled with the tag name
        name_input = modal.get_by_label("Name")
        expect(name_input).to_have_value(tag.name)

        # Change the tag name
        name_input.fill("new-name")

        # Submit the form
        modal.get_by_text("Save").click()

        # Verify modal is closed
        expect(modal).not_to_be_visible()

        # Verify the updated tag is shown in the list
        expect(self.locate_tag_row("new-name")).to_be_visible()
        expect(self.locate_tag_row("old-name")).not_to_be_visible()

        # Verify the tag was updated in the database
        tag.refresh_from_db()
        self.assertEqual(tag.name, "new-name")

    def test_edit_tag_validation_error(self):
        tag = self.setup_tag(name="tag-to-edit")
        other_tag = self.setup_tag(name="other-tag")

        self.open(reverse("linkding:tags.index"))

        # Click the Edit button for the tag
        tag_row = self.locate_tag_row(tag.name)
        tag_row.get_by_role("link", name="Edit").click()

        modal = self.locate_tag_modal()

        # Clear the name and submit
        name_input = modal.get_by_label("Name")
        name_input.fill("")
        modal.get_by_text("Save").click()

        # Verify the error is shown (field is required)
        error_hint = modal.get_by_text("This field is required")
        expect(error_hint).to_be_visible()

        # Fill in the name of another existing tag
        name_input.fill(other_tag.name)
        modal.get_by_text("Save").click()

        # Verify the error is shown (tag already exists)
        error_hint = modal.get_by_text('Tag "other-tag" already exists')
        expect(error_hint).to_be_visible()

        # Verify the tag was not modified
        tag.refresh_from_db()
        self.assertEqual(tag.name, "tag-to-edit")

    def test_edit_tag_preserves_query_and_scroll_position(self):
        # Create enough tags to have multiple pages (50 per page)
        for i in range(70):
            self.setup_tag(name=f"test-tag-{i:02d}")

        # Open tags page 2 with search query
        url = reverse("linkding:tags.index") + "?search=test&page=2"
        self.open(url)

        # Verify we're on page 2
        expect(self.locate_tag_row("test-tag-00")).not_to_be_visible()
        expect(self.locate_tag_row("test-tag-50")).to_be_visible()
        expect(self.locate_tag_row("test-tag-60")).to_be_visible()

        # Scroll down
        self.page.evaluate("window.scrollTo(0, 300)")
        initial_scroll = self.page.evaluate("window.scrollY")
        self.assertGreater(initial_scroll, 0)

        # Edit tag
        tag_row = self.locate_tag_row("test-tag-55")
        tag_row.get_by_role("link", name="Edit").click()

        modal = self.locate_tag_modal()

        name_input = modal.get_by_label("Name")
        name_input.fill("test-tag-55-edited")

        modal.get_by_text("Save").click()

        expect(modal).not_to_be_visible()

        # Verify query parameters and scroll position are preserved
        current_url = self.page.url
        self.assertIn("search=test", current_url)
        self.assertIn("page=2", current_url)

        expect(self.locate_tag_row("test-tag-00")).not_to_be_visible()
        expect(self.locate_tag_row("test-tag-50")).to_be_visible()
        expect(self.locate_tag_row("test-tag-55-edited")).to_be_visible()
        expect(self.locate_tag_row("test-tag-60")).to_be_visible()

        final_scroll = self.page.evaluate("window.scrollY")
        self.assertEqual(initial_scroll, final_scroll)

    def test_delete_tag_preserves_query_and_scroll_position(self):
        # Create enough tags to have multiple pages (50 per page)
        for i in range(70):
            self.setup_tag(name=f"test-tag-{i:02d}")

        # Open tags page 2 with search query
        url = reverse("linkding:tags.index") + "?search=test&page=2"
        self.open(url)

        # Verify we're on page 2
        expect(self.locate_tag_row("test-tag-00")).not_to_be_visible()
        expect(self.locate_tag_row("test-tag-50")).to_be_visible()
        expect(self.locate_tag_row("test-tag-55")).to_be_visible()
        expect(self.locate_tag_row("test-tag-60")).to_be_visible()

        # Scroll down
        self.page.evaluate("window.scrollTo(0, 300)")
        initial_scroll = self.page.evaluate("window.scrollY")
        self.assertGreater(initial_scroll, 0)

        # Delete tag
        tag_row = self.locate_tag_row("test-tag-55")
        tag_row.get_by_role("button", name="Remove").click()
        self.locate_confirm_dialog().get_by_text("Confirm").click()

        # Verify query parameters and scroll position are preserved
        current_url = self.page.url
        self.assertIn("search=test", current_url)
        self.assertIn("page=2", current_url)

        expect(self.locate_tag_row("test-tag-00")).not_to_be_visible()
        expect(self.locate_tag_row("test-tag-50")).to_be_visible()
        expect(self.locate_tag_row("test-tag-55")).not_to_be_visible()
        expect(self.locate_tag_row("test-tag-60")).to_be_visible()

        final_scroll = self.page.evaluate("window.scrollY")
        self.assertEqual(initial_scroll, final_scroll)

    def test_merge_tags(self):
        target_tag = self.setup_tag(name="target-tag")
        merge_tag1 = self.setup_tag(name="merge-tag1")
        merge_tag2 = self.setup_tag(name="merge-tag2")

        # Create bookmarks with the merge tags
        bookmark1 = self.setup_bookmark(tags=[merge_tag1])
        bookmark2 = self.setup_bookmark(tags=[merge_tag2])

        self.open(reverse("linkding:tags.index"))

        # Click the Merge Tags button to open the modal
        self.page.get_by_text("Merge Tags", exact=True).click()

        modal = self.locate_merge_modal()

        # Fill in the target tag
        target_input = modal.get_by_label("Target tag")
        target_input.fill(target_tag.name)

        # Fill in the tags to merge
        merge_input = modal.get_by_label("Tags to merge")
        merge_input.fill(f"{merge_tag1.name} {merge_tag2.name}")

        # Submit the form
        modal.get_by_role("button", name="Merge Tags").click()

        # Verify modal is closed
        expect(modal).not_to_be_visible()

        # Verify the success message is shown
        self.verify_success_message(
            'Successfully merged 2 tags (merge-tag1, merge-tag2) into "target-tag".'
        )

        # Verify the merged tags are no longer in the list
        expect(self.locate_tag_row("target-tag")).to_be_visible()
        expect(self.locate_tag_row("merge-tag1")).not_to_be_visible()
        expect(self.locate_tag_row("merge-tag2")).not_to_be_visible()

        # Verify the merge tags were deleted
        self.assertEqual(
            Tag.objects.filter(owner=self.get_or_create_test_user()).count(), 1
        )

        # Verify bookmarks only have the target tag
        bookmark1.refresh_from_db()
        bookmark2.refresh_from_db()
        self.assertCountEqual([target_tag], bookmark1.tags.all())
        self.assertCountEqual([target_tag], bookmark2.tags.all())

    def test_merge_tags_validation_error(self):
        target_tag = self.setup_tag(name="target-tag")
        merge_tag = self.setup_tag(name="merge-tag")

        self.open(reverse("linkding:tags.index"))

        # Click the Merge Tags button to open the modal
        self.page.get_by_text("Merge Tags", exact=True).click()

        modal = self.locate_merge_modal()

        # Submit with empty values
        modal.get_by_role("button", name="Merge Tags").click()

        # Verify the errors are shown
        expect(modal.get_by_text("This field is required").first).to_be_visible()

        # Fill in non-existent target tag
        target_input = modal.get_by_label("Target tag")
        target_input.fill("nonexistent-tag")

        merge_input = modal.get_by_label("Tags to merge")
        merge_input.fill(merge_tag.name)

        modal.get_by_role("button", name="Merge Tags").click()

        # Verify error for non-existent target tag
        expect(
            modal.get_by_text('Tag "nonexistent-tag" does not exist')
        ).to_be_visible()

        # Fill in valid target but target tag in merge tags
        target_input.fill(target_tag.name)
        merge_input.fill(target_tag.name)

        modal.get_by_role("button", name="Merge Tags").click()

        # Verify error for target tag in merge tags
        expect(
            modal.get_by_text("The target tag cannot be selected for merging")
        ).to_be_visible()

        # Verify no tags were deleted
        self.assertEqual(
            Tag.objects.filter(owner=self.get_or_create_test_user()).count(), 2
        )

    def test_search_updates_url_query_params(self):
        self.setup_tag(name="python")
        self.setup_tag(name="javascript")
        self.setup_tag(name="typescript")

        self.open(reverse("linkding:tags.index"))

        # Verify all tags are visible initially
        expect(self.locate_tag_row("python")).to_be_visible()
        expect(self.locate_tag_row("javascript")).to_be_visible()
        expect(self.locate_tag_row("typescript")).to_be_visible()

        # Enter search term and submit
        search_input = self.page.get_by_placeholder("Search tags...")
        search_input.fill("script")
        self.page.get_by_role("button", name="Search").click()

        # Wait for filtered results to appear
        expect(self.locate_tag_row("python")).not_to_be_visible()
        expect(self.locate_tag_row("javascript")).to_be_visible()
        expect(self.locate_tag_row("typescript")).to_be_visible()

        # Verify URL contains search query param
        self.assertIn("search=script", self.page.url)
