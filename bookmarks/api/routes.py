import gzip
import logging
import os

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter, DefaultRouter

from bookmarks import queries
from bookmarks.api.serializers import (
    BookmarkSerializer,
    BookmarkAssetSerializer,
    TagSerializer,
    UserProfileSerializer,
)
from bookmarks.models import Bookmark, BookmarkAsset, BookmarkSearch, Tag, User
from bookmarks.services import assets, bookmarks, auto_tagging, website_loader
from bookmarks.type_defs import HttpRequest
from bookmarks.views import access

logger = logging.getLogger(__name__)


class BookmarkViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    request: HttpRequest
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
        # Provide filtered queryset for list actions
        user = self.request.user
        search = BookmarkSearch.from_request(self.request.GET)
        if self.action == "list":
            return queries.query_bookmarks(user, user.profile, search)
        elif self.action == "archived":
            return queries.query_archived_bookmarks(user, user.profile, search)
        elif self.action == "shared":
            user = User.objects.filter(username=search.user).first()
            public_only = not self.request.user.is_authenticated
            return queries.query_shared_bookmarks(
                user, self.request.user_profile, search, public_only
            )

        # For single entity actions return user owned bookmarks
        return Bookmark.objects.all().filter(owner=user)

    def get_serializer_context(self):
        disable_scraping = "disable_scraping" in self.request.GET
        disable_html_snapshot = "disable_html_snapshot" in self.request.GET
        return {
            "request": self.request,
            "user": self.request.user,
            "disable_scraping": disable_scraping,
            "disable_html_snapshot": disable_html_snapshot,
        }

    @action(methods=["get"], detail=False)
    def archived(self, request: HttpRequest):
        return self.list(request)

    @action(methods=["get"], detail=False)
    def shared(self, request: HttpRequest):
        return self.list(request)

    @action(methods=["post"], detail=True)
    def archive(self, request: HttpRequest, pk):
        bookmark = self.get_object()
        bookmarks.archive_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["post"], detail=True)
    def unarchive(self, request: HttpRequest, pk):
        bookmark = self.get_object()
        bookmarks.unarchive_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=False)
    def check(self, request: HttpRequest):
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

    @action(methods=["post"], detail=False)
    def singlefile(self, request: HttpRequest):
        if settings.LD_DISABLE_ASSET_UPLOAD:
            return Response(
                {"error": "Asset upload is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        url = request.POST.get("url")
        file = request.FILES.get("file")

        if not url or not file:
            return Response(
                {"error": "Both 'url' and 'file' parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bookmark = Bookmark.objects.filter(owner=request.user, url=url).first()

        if not bookmark:
            bookmark = Bookmark(url=url)
            bookmark = bookmarks.create_bookmark(
                bookmark, "", request.user, disable_html_snapshot=True
            )
            bookmarks.enhance_with_website_metadata(bookmark)

        assets.upload_snapshot(bookmark, file.read())

        return Response(
            {"message": "Snapshot uploaded successfully."},
            status=status.HTTP_201_CREATED,
        )


class BookmarkAssetViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
):
    request: HttpRequest
    serializer_class = BookmarkAssetSerializer

    def get_queryset(self):
        user = self.request.user
        # limit access to assets to the owner of the bookmark for now
        bookmark = access.bookmark_write(self.request, self.kwargs["bookmark_id"])
        return BookmarkAsset.objects.filter(
            bookmark_id=bookmark.id, bookmark__owner=user
        )

    def get_serializer_context(self):
        return {"user": self.request.user}

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request: HttpRequest, bookmark_id, pk):
        asset = self.get_object()
        try:
            file_path = os.path.join(settings.LD_ASSET_FOLDER, asset.file)
            content_type = asset.content_type
            file_stream = (
                gzip.GzipFile(file_path, mode="rb")
                if asset.gzip
                else open(file_path, "rb")
            )
            file_name = (
                f"{asset.display_name}.html"
                if asset.asset_type == BookmarkAsset.TYPE_SNAPSHOT
                else asset.display_name
            )
            response = FileResponse(file_stream, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
            return response
        except FileNotFoundError:
            raise Http404("Asset file does not exist")
        except Exception as e:
            logger.error(
                f"Failed to download asset. bookmark_id={bookmark_id}, asset_id={pk}",
                exc_info=e,
            )
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=["post"], detail=False)
    def upload(self, request: HttpRequest, bookmark_id):
        if settings.LD_DISABLE_ASSET_UPLOAD:
            return Response(
                {"error": "Asset upload is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        bookmark = access.bookmark_write(request, bookmark_id)

        upload_file = request.FILES.get("file")
        if not upload_file:
            return Response(
                {"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            asset = assets.upload_asset(bookmark, upload_file)
            serializer = self.get_serializer(asset)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(
                f"Failed to upload asset file. bookmark_id={bookmark_id}, file={upload_file.name}",
                exc_info=e,
            )
            return Response(
                {"error": "Failed to upload asset."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TagViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
):
    request: HttpRequest
    serializer_class = TagSerializer

    def get_queryset(self):
        user = self.request.user
        return Tag.objects.all().filter(owner=user)

    def get_serializer_context(self):
        return {"user": self.request.user}


class UserViewSet(viewsets.GenericViewSet):
    @action(methods=["get"], detail=False)
    def profile(self, request: HttpRequest):
        return Response(UserProfileSerializer(request.user.profile).data)


# DRF routers do not support nested view sets such as /bookmarks/<id>/assets/<id>/
# Instead create separate routers for each view set and manually register them in urls.py
# The default router is only used to allow reversing a URL for the API root
default_router = DefaultRouter()

bookmark_router = SimpleRouter()
bookmark_router.register("", BookmarkViewSet, basename="bookmark")

tag_router = SimpleRouter()
tag_router.register("", TagViewSet, basename="tag")

user_router = SimpleRouter()
user_router.register("", UserViewSet, basename="user")

bookmark_asset_router = SimpleRouter()
bookmark_asset_router.register("", BookmarkAssetViewSet, basename="bookmark_asset")
