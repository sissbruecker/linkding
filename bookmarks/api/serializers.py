from django.db.models import Max, prefetch_related_objects
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.serializers import ListSerializer

from bookmarks.models import (
    Bookmark,
    BookmarkAsset,
    Tag,
    build_tag_string,
    UserProfile,
    BookmarkBundle,
)
from bookmarks.services import bookmarks, bundles
from bookmarks.services.tags import get_or_create_tag
from bookmarks.services.wayback import generate_fallback_webarchive_url
from bookmarks.utils import app_version


class TagListField(serializers.ListField):
    child = serializers.CharField()


class BookmarkListSerializer(ListSerializer):
    def to_representation(self, data):
        # Prefetch nested relations to avoid n+1 queries
        prefetch_related_objects(data, "tags")

        return super().to_representation(data)


class EmtpyField(serializers.ReadOnlyField):
    def to_representation(self, value):
        return None


class BookmarkBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookmarkBundle
        fields = [
            "id",
            "name",
            "search",
            "any_tags",
            "all_tags",
            "excluded_tags",
            "order",
            "date_created",
            "date_modified",
        ]
        read_only_fields = [
            "id",
            "date_created",
            "date_modified",
        ]

    def create(self, validated_data):
        bundle = BookmarkBundle(**validated_data)
        bundle.order = validated_data["order"] if "order" in validated_data else None
        return bundles.create_bundle(bundle, self.context["user"])


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = [
            "id",
            "url",
            "title",
            "description",
            "notes",
            "web_archive_snapshot_url",
            "favicon_url",
            "preview_image_url",
            "is_archived",
            "unread",
            "shared",
            "tag_names",
            "date_added",
            "date_modified",
            "website_title",
            "website_description",
        ]
        read_only_fields = [
            "web_archive_snapshot_url",
            "favicon_url",
            "preview_image_url",
            "tag_names",
            "date_added",
            "date_modified",
            "website_title",
            "website_description",
        ]
        list_serializer_class = BookmarkListSerializer

    # Custom tag_names field to allow passing a list of tag names to create/update
    tag_names = TagListField(required=False)
    # Custom fields to generate URLs for favicon, preview image, and web archive snapshot
    favicon_url = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    web_archive_snapshot_url = serializers.SerializerMethodField()
    # Add dummy website title and description fields for backwards compatibility but keep them empty
    website_title = EmtpyField()
    website_description = EmtpyField()

    def get_favicon_url(self, obj: Bookmark):
        if not obj.favicon_file:
            return None
        request = self.context.get("request")
        favicon_file_path = static(obj.favicon_file)
        favicon_url = request.build_absolute_uri(favicon_file_path)
        return favicon_url

    def get_preview_image_url(self, obj: Bookmark):
        if not obj.preview_image_file:
            return None
        request = self.context.get("request")
        preview_image_file_path = static(obj.preview_image_file)
        preview_image_url = request.build_absolute_uri(preview_image_file_path)
        return preview_image_url

    def get_web_archive_snapshot_url(self, obj: Bookmark):
        if obj.web_archive_snapshot_url:
            return obj.web_archive_snapshot_url

        return generate_fallback_webarchive_url(obj.url, obj.date_added)

    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", [])
        tag_string = build_tag_string(tag_names)
        bookmark = Bookmark(**validated_data)

        disable_scraping = self.context.get("disable_scraping", False)
        disable_html_snapshot = self.context.get("disable_html_snapshot", False)

        saved_bookmark = bookmarks.create_bookmark(
            bookmark,
            tag_string,
            self.context["user"],
            disable_html_snapshot=disable_html_snapshot,
        )
        # Unless scraping is explicitly disabled, enhance bookmark with website
        # metadata to preserve backwards compatibility with clients that expect
        # title and description to be populated automatically when left empty
        if not disable_scraping:
            bookmarks.enhance_with_website_metadata(saved_bookmark)
        return saved_bookmark

    def update(self, instance: Bookmark, validated_data):
        tag_names = validated_data.pop("tag_names", instance.tag_names)
        tag_string = build_tag_string(tag_names)

        for field_name, field in self.fields.items():
            if not field.read_only and field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])

        return bookmarks.update_bookmark(instance, tag_string, self.context["user"])

    def validate(self, attrs):
        # When creating a bookmark, the service logic prevents duplicate URLs by
        # updating the existing bookmark instead. When editing a bookmark,
        # there is no assumption that it would update a different bookmark if
        # the URL is a duplicate, so raise a validation error in that case.
        if self.instance and "url" in attrs:
            is_duplicate = (
                Bookmark.objects.filter(owner=self.instance.owner, url=attrs["url"])
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if is_duplicate:
                raise serializers.ValidationError(
                    {"url": "A bookmark with this URL already exists."}
                )

        return attrs


class BookmarkAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookmarkAsset
        fields = [
            "id",
            "bookmark",
            "date_created",
            "file_size",
            "asset_type",
            "content_type",
            "display_name",
            "status",
        ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "date_added"]
        read_only_fields = ["date_added"]

    def create(self, validated_data):
        return get_or_create_tag(validated_data["name"], self.context["user"])


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "theme",
            "bookmark_date_display",
            "bookmark_link_target",
            "web_archive_integration",
            "tag_search",
            "enable_sharing",
            "enable_public_sharing",
            "enable_favicons",
            "display_url",
            "permanent_notes",
            "search_preferences",
            "version",
        ]

    version = serializers.ReadOnlyField(default=app_version)
