from django.db.models import prefetch_related_objects
from django.templatetags.static import static
from rest_framework import serializers
from rest_framework.serializers import ListSerializer

from bookmarks.models import Bookmark, Tag, build_tag_string, UserProfile
from bookmarks.services.bookmarks import create_bookmark, update_bookmark
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
            "website_title",
            "website_description",
            "web_archive_snapshot_url",
            "favicon_url",
            "preview_image_url",
            "is_archived",
            "unread",
            "shared",
            "tag_names",
            "date_added",
            "date_modified",
        ]
        read_only_fields = [
            "website_title",
            "website_description",
            "web_archive_snapshot_url",
            "favicon_url",
            "preview_image_url",
            "date_added",
            "date_modified",
        ]
        list_serializer_class = BookmarkListSerializer

    # Override optional char fields to provide default value
    title = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    is_archived = serializers.BooleanField(required=False, default=False)
    unread = serializers.BooleanField(required=False, default=False)
    shared = serializers.BooleanField(required=False, default=False)
    # Override readonly tag_names property to allow passing a list of tag names to create/update
    tag_names = TagListField(required=False, default=[])
    favicon_url = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()

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

    def create(self, validated_data):
        bookmark = Bookmark()
        bookmark.url = validated_data["url"]
        bookmark.title = validated_data["title"]
        bookmark.description = validated_data["description"]
        bookmark.notes = validated_data["notes"]
        bookmark.is_archived = validated_data["is_archived"]
        bookmark.unread = validated_data["unread"]
        bookmark.shared = validated_data["shared"]
        tag_string = build_tag_string(validated_data["tag_names"])
        return create_bookmark(bookmark, tag_string, self.context["user"])

    def update(self, instance: Bookmark, validated_data):
        # Update fields if they were provided in the payload
        for key in ["url", "title", "description", "notes", "unread", "shared"]:
            if key in validated_data:
                setattr(instance, key, validated_data[key])

        # Use tag string from payload, or use bookmark's current tags as fallback
        tag_string = build_tag_string(instance.tag_names)
        if "tag_names" in validated_data:
            tag_string = build_tag_string(validated_data["tag_names"])

        return update_bookmark(instance, tag_string, self.context["user"])


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
