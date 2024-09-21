import logging

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from bookmarks import queries
from bookmarks.api.serializers import (
    BookmarkSerializer,
    TagSerializer,
    UserProfileSerializer,
)
from bookmarks.models import Bookmark, BookmarkSearch, Tag, User
from bookmarks.services import auto_tagging
from bookmarks.services.bookmarks import (
    archive_bookmark,
    unarchive_bookmark,
    website_loader,
)
from bookmarks.services.website_loader import WebsiteMetadata

logger = logging.getLogger(__name__)


class BookmarkViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    serializer_class = BookmarkSerializer

    def get_permissions(self):
        # Allow unauthenticated access to shared bookmarks.
        # The shared action should still filter bookmarks so that
        # unauthenticated users only see bookmarks from users that have public
        # sharing explicitly enabled
        if self.action == "shared":
            return [AllowAny()]

        # Otherwise use default permissions which should require authentication
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        # For list action, use query set that applies search and tag projections
        if self.action == "list":
            search = BookmarkSearch.from_request(self.request.GET)
            return queries.query_bookmarks(user, user.profile, search)

        # For single entity actions use default query set without projections
        return Bookmark.objects.all().filter(owner=user)

    def get_serializer_context(self):
        disable_scraping = "disable_scraping" in self.request.GET
        return {
            "request": self.request,
            "user": self.request.user,
            "disable_scraping": disable_scraping,
        }

    @action(methods=["get"], detail=False)
    def archived(self, request):
        user = request.user
        search = BookmarkSearch.from_request(request.GET)
        query_set = queries.query_archived_bookmarks(user, user.profile, search)
        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer(page, many=True)
        data = serializer.data
        return self.get_paginated_response(data)

    @action(methods=["get"], detail=False)
    def shared(self, request):
        search = BookmarkSearch.from_request(request.GET)
        user = User.objects.filter(username=search.user).first()
        public_only = not request.user.is_authenticated
        query_set = queries.query_shared_bookmarks(
            user, request.user_profile, search, public_only
        )
        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer(page, many=True)
        data = serializer.data
        return self.get_paginated_response(data)

    @action(methods=["post"], detail=True)
    def archive(self, request, pk):
        bookmark = self.get_object()
        archive_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["post"], detail=True)
    def unarchive(self, request, pk):
        bookmark = self.get_object()
        unarchive_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=False)
    def check(self, request):
        url = request.GET.get("url")
        bookmark = Bookmark.objects.filter(owner=request.user, url=url).first()
        existing_bookmark_data = (
            self.get_serializer(bookmark).data if bookmark else None
        )

        metadata = website_loader.load_website_metadata(url)

        # Return tags that would be automatically applied to the bookmark
        profile = request.user.profile
        auto_tags = []
        if profile.auto_tagging_rules:
            try:
                auto_tags = auto_tagging.get_tags(profile.auto_tagging_rules, url)
            except Exception as e:
                logger.error(
                    f"Failed to auto-tag bookmark. url={url}",
                    exc_info=e,
                )

        return Response(
            {
                "bookmark": existing_bookmark_data,
                "metadata": metadata.to_dict(),
                "auto_tags": auto_tags,
            },
            status=status.HTTP_200_OK,
        )


class TagViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
):
    serializer_class = TagSerializer

    def get_queryset(self):
        user = self.request.user
        return Tag.objects.all().filter(owner=user)

    def get_serializer_context(self):
        return {"user": self.request.user}


class UserViewSet(viewsets.GenericViewSet):
    @action(methods=["get"], detail=False)
    def profile(self, request):
        return Response(UserProfileSerializer(request.user.profile).data)


router = DefaultRouter()
router.register(r"bookmarks", BookmarkViewSet, basename="bookmark")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"user", UserViewSet, basename="user")
