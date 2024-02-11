from django.db.models import prefetch_related_objects
from rest_framework import serializers
from rest_framework.serializers import ListSerializer

from bookmarks.models import Bookmark, Link, Tag, build_tag_string, UserProfile
from bookmarks.services.bookmarks import create_bookmark, update_bookmark
from bookmarks.services.tags import get_or_create_tag


class TagListField(serializers.ListField):
    child = serializers.CharField()


class BookmarkListSerializer(ListSerializer):
    def to_representation(self, data):
        # Prefetch nested relations to avoid n+1 queries
        prefetch_related_objects(data, "tags")
        representation = super().to_representation(data)
        return representation


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = [
            "id",
            "url",
            "title",
            "description",
            "notes",
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
            "date_added",
            "date_modified",
        ]
        list_serializer_class = BookmarkListSerializer

    url = serializers.CharField(required=False)
    # Override optional char fields to provide default value
    title = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    is_archived = serializers.BooleanField(required=False, default=False)
    unread = serializers.BooleanField(required=False, default=False)
    shared = serializers.BooleanField(required=False, default=False)
    # Override readonly tag_names property to allow passing a list of tag names to create/update
    tag_names = TagListField(required=False, default=[])

    def to_representation(self, data):
        result = super().to_representation(data)
        result["url"] = data.link.url
        result["website_description"] = data.link.website_description
        result["website_title"] = data.link.website_title
        return result

    def create(self, validated_data):
        link = Link(url=validated_data["url"])
        bookmark = Bookmark()
        bookmark.link = link
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

        if validated_data.get("url") and validated_data["url"] != instance.link.url:
            instance.link = Link(url=validated_data["url"])

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
