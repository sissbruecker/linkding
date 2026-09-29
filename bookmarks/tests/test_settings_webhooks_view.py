from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from bookmarks.models import Webhook
from bookmarks.services import http_client
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin

ALL_EVENTS = [event for event, _ in Webhook.EVENT_CHOICES]


class SettingsWebhooksViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def get_webhooks_section(self):
        response = self.client.get(reverse("linkding:settings.integrations"))
        soup = self.make_soup(response.content.decode())
        return soup.find("turbo-frame", id="webhooks-section")

    def test_should_check_authentication(self):
        self.client.logout()
        urls = [
            reverse("linkding:settings.integrations.create_webhook"),
            reverse("linkding:settings.integrations.edit_webhook", args=[1]),
            reverse("linkding:settings.integrations.delete_webhook"),
            reverse("linkding:settings.integrations.test_webhook"),
        ]
        for url in urls:
            response = self.client.post(url)
            self.assertEqual(302, response.status_code, msg=url)
            self.assertTrue(response.url.startswith(settings.LOGIN_URL), msg=url)

    def test_list_webhooks(self):
        self.setup_webhook(name="Webhook 1", url="https://example.com/1")
        self.setup_webhook(name="Webhook 2", url="https://example.com/2", enabled=False)
        self.setup_webhook(user=self.setup_user(), name="Other user's webhook")

        section = self.get_webhooks_section()
        rows = section.find("table").find("tbody").find_all("tr")

        self.assertEqual(2, len(rows))
        cells = rows[0].find_all("td")
        self.assertEqual("Webhook 2(disabled)", cells[0].get_text(strip=True))
        self.assertEqual("https://example.com/2", cells[1].get_text(strip=True))
        self.assertEqual("Never", cells[2].get_text(strip=True))
        cells = rows[1].find_all("td")
        self.assertEqual("Webhook 1", cells[0].get_text(strip=True))
        self.assertNotIn("Other user's webhook", section.get_text())

    def test_list_webhooks_shows_last_delivery(self):
        webhook = self.setup_webhook()
        webhook.last_delivery_date = webhook.date_created
        webhook.last_delivery_status = Webhook.DELIVERY_STATUS_FAILURE
        webhook.last_delivery_message = "HTTP 500"
        webhook.save()

        section = self.get_webhooks_section()
        cell = section.find("tbody").find_all("td")[2]

        self.assertEqual("HTTP 500", cell.find("span", class_="text-error").text)

    def test_no_table_without_webhooks(self):
        section = self.get_webhooks_section()

        self.assertIsNone(section.find("table"))

    def test_shows_warning_when_background_tasks_disabled(self):
        section = self.get_webhooks_section()
        self.assertIsNone(section.find(class_="toast-warning"))

        with override_settings(LD_DISABLE_BACKGROUND_TASKS=True):
            section = self.get_webhooks_section()
        self.assertIsNotNone(section.find(class_="toast-warning"))

    def test_create_webhook_modal(self):
        response = self.client.get(
            reverse("linkding:settings.integrations.create_webhook")
        )
        soup = self.make_soup(response.content.decode())

        self.assertEqual(200, response.status_code)
        # All events and enabled are selected by default
        for event in ALL_EVENTS:
            checkbox = soup.find("input", {"name": "events", "value": event})
            self.assertTrue(checkbox.has_attr("checked"), msg=event)
        self.assertTrue(soup.find("input", {"name": "enabled"}).has_attr("checked"))

    def test_create_webhook(self):
        response = self.client.post(
            reverse("linkding:settings.integrations.create_webhook"),
            {
                "name": "My webhook",
                "url": "https://example.com/webhook",
                "events": [
                    Webhook.EVENT_BOOKMARK_DELETED,
                    Webhook.EVENT_BOOKMARK_CREATED,
                ],
                "enabled": "on",
            },
        )

        self.assertRedirects(response, reverse("linkding:settings.integrations"))
        webhook = Webhook.objects.get()
        self.assertEqual(self.user, webhook.owner)
        self.assertEqual("My webhook", webhook.name)
        self.assertEqual("https://example.com/webhook", webhook.url)
        # Events are stored in a consistent order
        self.assertEqual(
            [Webhook.EVENT_BOOKMARK_CREATED, Webhook.EVENT_BOOKMARK_DELETED],
            webhook.events,
        )
        self.assertTrue(webhook.enabled)
        self.assertTrue(webhook.secret.startswith("whsec_"))

    def test_create_webhook_shows_secret_once(self):
        self.client.post(
            reverse("linkding:settings.integrations.create_webhook"),
            {"name": "Webhook", "url": "https://example.com", "events": ALL_EVENTS},
        )
        webhook = Webhook.objects.get()

        response = self.client.get(reverse("linkding:settings.integrations"))
        self.assertContains(response, webhook.secret)
        section = self.make_soup(response.content.decode()).find(
            "turbo-frame", id="webhooks-section"
        )
        self.assertEqual(
            'Webhook "Webhook" created successfully',
            section.find(class_="toast-success").text,
        )

        response = self.client.get(reverse("linkding:settings.integrations"))
        self.assertNotContains(response, webhook.secret)

    def test_create_webhook_validation(self):
        invalid_data = [
            {"name": "", "url": "https://example.com", "events": ALL_EVENTS},
            {"name": "Webhook", "url": "", "events": ALL_EVENTS},
            {"name": "Webhook", "url": "not a url", "events": ALL_EVENTS},
            {"name": "Webhook", "url": "ftp://example.com", "events": ALL_EVENTS},
            {"name": "Webhook", "url": "https://example.com", "events": []},
            {"name": "Webhook", "url": "https://example.com", "events": ["invalid"]},
        ]

        for data in invalid_data:
            response = self.client.post(
                reverse("linkding:settings.integrations.create_webhook"), data
            )

            self.assertEqual(200, response.status_code, msg=data)
            self.assertEqual(
                "text/vnd.turbo-stream.html", response["Content-Type"], msg=data
            )
            self.assertContains(response, 'target="webhook-modal"')
            self.assertContains(response, "form-input-hint is-error")
            self.assertEqual(0, Webhook.objects.count(), msg=data)

    def test_edit_webhook_modal(self):
        webhook = self.setup_webhook(
            name="Webhook", events=[Webhook.EVENT_BOOKMARK_CREATED]
        )

        response = self.client.get(
            reverse("linkding:settings.integrations.edit_webhook", args=[webhook.id])
        )
        soup = self.make_soup(response.content.decode())

        self.assertEqual("Webhook", soup.find("input", {"name": "name"})["value"])
        self.assertTrue(
            soup.find(
                "input", {"name": "events", "value": Webhook.EVENT_BOOKMARK_CREATED}
            ).has_attr("checked")
        )
        self.assertFalse(
            soup.find(
                "input", {"name": "events", "value": Webhook.EVENT_BOOKMARK_DELETED}
            ).has_attr("checked")
        )
        # Secret is not shown again
        self.assertNotContains(response, webhook.secret)

    def test_edit_webhook(self):
        webhook = self.setup_webhook()
        secret = webhook.secret

        response = self.client.post(
            reverse("linkding:settings.integrations.edit_webhook", args=[webhook.id]),
            {
                "name": "Updated",
                "url": "https://example.com/updated",
                "events": [Webhook.EVENT_BOOKMARK_ARCHIVED],
            },
        )

        self.assertRedirects(response, reverse("linkding:settings.integrations"))
        webhook.refresh_from_db()
        self.assertEqual("Updated", webhook.name)
        self.assertEqual("https://example.com/updated", webhook.url)
        self.assertEqual([Webhook.EVENT_BOOKMARK_ARCHIVED], webhook.events)
        self.assertFalse(webhook.enabled)
        self.assertEqual(secret, webhook.secret)

    def test_edit_webhook_validation(self):
        webhook = self.setup_webhook(name="Webhook")

        response = self.client.post(
            reverse("linkding:settings.integrations.edit_webhook", args=[webhook.id]),
            {"name": "", "url": "https://example.com", "events": ALL_EVENTS},
        )

        self.assertEqual("text/vnd.turbo-stream.html", response["Content-Type"])
        webhook.refresh_from_db()
        self.assertEqual("Webhook", webhook.name)

    def test_edit_webhook_wrong_user(self):
        webhook = self.setup_webhook(user=self.setup_user(), name="Other")
        url = reverse("linkding:settings.integrations.edit_webhook", args=[webhook.id])

        self.assertEqual(404, self.client.get(url).status_code)
        response = self.client.post(
            url, {"name": "Changed", "url": "https://example.com", "events": ALL_EVENTS}
        )
        self.assertEqual(404, response.status_code)
        webhook.refresh_from_db()
        self.assertEqual("Other", webhook.name)

    def test_delete_webhook(self):
        webhook = self.setup_webhook(name="To delete")

        response = self.client.post(
            reverse("linkding:settings.integrations.delete_webhook"),
            {"webhook_id": webhook.id},
        )

        self.assertRedirects(response, reverse("linkding:settings.integrations"))
        self.assertEqual(0, Webhook.objects.count())

    def test_delete_webhook_wrong_user(self):
        webhook = self.setup_webhook(user=self.setup_user())

        response = self.client.post(
            reverse("linkding:settings.integrations.delete_webhook"),
            {"webhook_id": webhook.id},
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual(1, Webhook.objects.count())

    def test_delete_webhook_invalid_id(self):
        response = self.client.post(
            reverse("linkding:settings.integrations.delete_webhook"),
            {"webhook_id": "invalid"},
        )

        self.assertEqual(404, response.status_code)

    @mock.patch.object(http_client, "post")
    def test_test_webhook_success(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200)
        webhook = self.setup_webhook(name="Webhook", enabled=False)

        response = self.client.post(
            reverse("linkding:settings.integrations.test_webhook"),
            {"webhook_id": webhook.id},
            follow=True,
        )

        mock_post.assert_called_once()
        soup = self.make_soup(response.content.decode())
        self.assertEqual(
            'Test message sent to webhook "Webhook" successfully (HTTP 200).',
            soup.find(class_="toast-success").text,
        )
        webhook.refresh_from_db()
        self.assertEqual(Webhook.DELIVERY_STATUS_SUCCESS, webhook.last_delivery_status)

    @mock.patch.object(http_client, "post")
    def test_test_webhook_failure(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=500)
        webhook = self.setup_webhook(name="Webhook")

        response = self.client.post(
            reverse("linkding:settings.integrations.test_webhook"),
            {"webhook_id": webhook.id},
            follow=True,
        )

        soup = self.make_soup(response.content.decode())
        error = soup.find(class_="toast-error")
        self.assertIn('Failed to send test message to webhook "Webhook"', error.text)
        self.assertIn("HTTP 500", error.text)

    @mock.patch.object(http_client, "post")
    def test_test_webhook_wrong_user(self, mock_post):
        webhook = self.setup_webhook(user=self.setup_user())

        response = self.client.post(
            reverse("linkding:settings.integrations.test_webhook"),
            {"webhook_id": webhook.id},
        )

        self.assertEqual(404, response.status_code)
        mock_post.assert_not_called()
