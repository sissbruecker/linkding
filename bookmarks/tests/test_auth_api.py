from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from bookmarks.tests.helpers import LinkdingApiTestCase, BookmarkFactoryMixin


class AuthApiTestCase(LinkdingApiTestCase, BookmarkFactoryMixin):

    def authenticate(self, keyword):
        self.api_token = Token.objects.get_or_create(
            user=self.get_or_create_test_user()
        )[0]
        self.client.credentials(HTTP_AUTHORIZATION=f"{keyword} {self.api_token.key}")

    def test_auth_with_token_keyword(self):
        self.authenticate("Token")

        url = reverse("linkding:user-profile")
        self.get(url, expected_status_code=status.HTTP_200_OK)

    def test_auth_with_bearer_keyword(self):
        self.authenticate("Bearer")

        url = reverse("linkding:user-profile")
        self.get(url, expected_status_code=status.HTTP_200_OK)

    def test_auth_with_unknown_keyword(self):
        self.authenticate("Key")

        url = reverse("linkding:user-profile")
        self.get(url, expected_status_code=status.HTTP_401_UNAUTHORIZED)
