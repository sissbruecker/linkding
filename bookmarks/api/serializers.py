from rest_framework import serializers

from bookmarks.models import Bookmark, Tag, build_tag_string
from bookmarks.services.bookmarks import create_bookmark, update_bookmark
from bookmarks.services.tags import get_or_create_tag


class TagListField(serializers.ListField):
    child = serializers.CharField()


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = [
            'id',
            'url',
            'title',
            'description',
            'website_title',
            'website_description',
            'tag_names',
            'date_added',
            'date_modified'
        ]
        read_only_fields = [
            'website_title',
            'website_description',
            'date_added',
            'date_modified'
        ]

    # Override optional char fields to provide default value
    title = serializers.CharField(required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    # Override readonly tag_names property to allow passing a list of tag names to create/update
    tag_names = TagListField(required=False, default=[])

    def create(self, validated_data):
        bookmark = Bookmark()
        bookmark.url = validated_data['url']
        bookmark.title = validated_data['title']
        bookmark.description = validated_data['description']
        tag_string = build_tag_string(validated_data['tag_names'])
        return create_bookmark(bookmark, tag_string, self.context['user'])

    def update(self, instance: Bookmark, validated_data):
        instance.url = validated_data['url']
        instance.title = validated_data['title']
        instance.description = validated_data['description']
        tag_string = build_tag_string(validated_data['tag_names'])
        return update_bookmark(instance, tag_string, self.context['user'])


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'date_added']
        read_only_fields = ['date_added']

    def create(self, validated_data):
        return get_or_create_tag(validated_data['name'], self.context['user'])
