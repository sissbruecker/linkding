from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Toast
from bookmarks.tests.helpers import BookmarkFactoryMixin, random_sentence, disable_logging


class ToastsViewTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)

    def create_toast(self, user: User = None, message: str = None, acknowledged: bool = False):
        if not user:
            user = self.user
        if not message:
            message = random_sentence()

        toast = Toast(owner=user, key='test', message=message, acknowledged=acknowledged)
        toast.save()
        return toast

    def test_should_render_unacknowledged_toasts(self):
        self.create_toast()
        self.create_toast()
        self.create_toast(acknowledged=True)

        response = self.client.get(reverse('bookmarks:index'))

        # Should render toasts container
        self.assertContains(response, '<div class="toasts container grid-lg">')
        # Should render two toasts
        self.assertContains(response, '<div class="toast">', count=2)

    def test_should_not_render_acknowledged_toasts(self):
        self.create_toast(acknowledged=True)
        self.create_toast(acknowledged=True)
        self.create_toast(acknowledged=True)

        response = self.client.get(reverse('bookmarks:index'))

        # Should not render toasts container
        self.assertContains(response, '<div class="toasts container grid-lg">', count=0)
        # Should not render toasts
        self.assertContains(response, '<div class="toast">', count=0)

    def test_should_not_render_toasts_of_other_users(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')

        self.create_toast(user=other_user)
        self.create_toast(user=other_user)
        self.create_toast(user=other_user)

        response = self.client.get(reverse('bookmarks:index'))

        # Should not render toasts container
        self.assertContains(response, '<div class="toasts container grid-lg">', count=0)
        # Should not render toasts
        self.assertContains(response, '<div class="toast">', count=0)

    def test_toast_content(self):
        toast = self.create_toast()
        expected_toast = f'''
            <div class="toast">
                {toast.message}
                <a href="{reverse('bookmarks:toasts.acknowledge', args=[toast.id])}?return_url={reverse('bookmarks:index')}" class="btn btn-clear float-right"></a>
            </div>        
        '''

        response = self.client.get(reverse('bookmarks:index'))
        html = response.content.decode()

        self.assertInHTML(expected_toast, html)

    def test_acknowledge_toast(self):
        toast = self.create_toast()

        self.client.get(reverse('bookmarks:toasts.acknowledge', args=[toast.id]))

        toast.refresh_from_db()
        self.assertTrue(toast.acknowledged)

    def test_acknowledge_toast_should_redirect_to_return_url(self):
        toast = self.create_toast()
        return_url = reverse('bookmarks:settings.general')
        acknowledge_url = reverse('bookmarks:toasts.acknowledge', args=[toast.id])
        acknowledge_url = acknowledge_url + '?return_url=' + return_url

        response = self.client.get(acknowledge_url)

        self.assertRedirects(response, return_url)

    def test_acknowledge_toast_should_redirect_to_index_by_default(self):
        toast = self.create_toast()

        response = self.client.get(reverse('bookmarks:toasts.acknowledge', args=[toast.id]))

        self.assertRedirects(response, reverse('bookmarks:index'))

    @disable_logging
    def test_acknowledge_toast_should_not_acknowledge_other_users_toast(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        toast = self.create_toast(user=other_user)

        response = self.client.get(reverse('bookmarks:toasts.acknowledge', args=[toast.id]))
        self.assertEqual(response.status_code, 404)
