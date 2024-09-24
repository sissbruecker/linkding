from django.db.models import prefetch_related_objects
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.serializers import ListSerializer

from bookmarks.models import Bookmark, Tag, build_tag_string, UserProfile
from bookmarks.services.bookmarks import (
    create_bookmark,
    update_bookmark,
    enhance_with_website_metadata,
)
from bookmarks.services.tags import get_or_create_tag


class TagListField(serializers.ListField):
    child = serializers.CharField()


class BookmarkListSerializer(ListSerializer):
    def to_representation(self, data):
        # Prefetch nested relations to avoid n+1 queries
        prefetch_related_objects(data, "tags")

        return super().to_representation(data)


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
    # Custom fields to return URLs for favicon and preview image
    favicon_url = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    # Add dummy website title and description fields for backwards compatibility but keep them empty
    website_title = serializers.SerializerMethodField()
    website_description = serializers.SerializerMethodField()

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

    def get_website_title(self, obj: Bookmark):
        return None

    def get_website_description(self, obj: Bookmark):
        return None

    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", [])
        tag_string = build_tag_string(tag_names)
        bookmark = Bookmark(**validated_data)

        saved_bookmark = create_bookmark(bookmark, tag_string, self.context["user"])
        # Unless scraping is explicitly disabled, enhance bookmark with website
        # metadata to preserve backwards compatibility with clients that expect
        # title and description to be populated automatically when left empty
        if not self.context.get("disable_scraping", False):
            enhance_with_website_metadata(saved_bookmark)
        return saved_bookmark

    def update(self, instance: Bookmark, validated_data):
        tag_names = validated_data.pop("tag_names", instance.tag_names)
        tag_string = build_tag_string(tag_names)

        for field_name, field in self.fields.items():
            if not field.read_only and field_name in validated_data:
                setattr(instance, field_name, validated_data[field_name])

        return update_bookmark(instance, tag_string, self.context["user"])

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
        ]
