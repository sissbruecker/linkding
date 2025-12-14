from django.urls import reverse
from playwright.sync_api import sync_playwright, expect

from bookmarks.tests_e2e.helpers import LinkdingE2ETestCase


class SettingsIntegrationsE2ETestCase(LinkdingE2ETestCase):
    def test_create_api_token(self):
        with sync_playwright() as p:
            self.open(reverse("linkding:settings.integrations"), p)

            # Click create API token button
            self.page.get_by_text("Create API token").click()

            # Wait for modal to appear
            modal = self.page.locator(".modal")
            expect(modal).to_be_visible()

            # Enter custom token name
            token_name_input = modal.locator("#token-name")
            token_name_input.fill("")
            token_name_input.fill("My Test Token")

            # Confirm the dialog
            modal.page.get_by_role("button", name="Create Token").click()

            # Verify the API token key is shown in the input
            new_token_input = self.page.locator("#new-token-key")
            expect(new_token_input).to_be_visible()
            token_value = new_token_input.input_value()
            self.assertTrue(len(token_value) > 0)

            # Verify the API token is now listed in the table
            token_table = self.page.locator("table.crud-table")
            expect(token_table).to_be_visible()
            expect(token_table.get_by_text("My Test Token")).to_be_visible()

            # Verify the dialog is gone
            expect(modal).to_be_hidden()

            # Reload the page to verify the API token key is only shown once
            self.page.reload()

            # Token key input should no longer be visible
            expect(new_token_input).not_to_be_visible()

            # But the token should still be listed in the table
            expect(token_table.get_by_text("My Test Token")).to_be_visible()

    def test_delete_api_token(self):
        self.setup_api_token(name="Token To Delete")

        with sync_playwright() as p:
            self.open(reverse("linkding:settings.integrations"), p)

            token_table = self.page.locator("table.crud-table")
            expect(token_table.get_by_text("Token To Delete")).to_be_visible()

            # Click delete button for the token
            token_row = token_table.locator("tr").filter(has_text="Token To Delete")
            token_row.get_by_role("button", name="Delete").click()

            # Confirm deletion
            self.locate_confirm_dialog().get_by_text("Confirm").click()

            # Verify the token is removed from the table
            expect(token_table.get_by_text("Token To Delete")).not_to_be_visible()
