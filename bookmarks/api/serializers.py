from rest_framework import serializers

from bookmarks.models import Bookmark, build_tag_string
from bookmarks.services.bookmarks import create_bookmark, update_bookmark


class TagListField(serializers.ListField):
    child = serializers.CharField()


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['id', 'url', 'title', 'description', 'tag_names']

    # Override readonly tag_names property to allow passing a list of tag names to create/update
    tag_names = TagListField()

    def create(self, validated_data):
        bookmark = Bookmark()
        bookmark.url = validated_data['url']
        bookmark.title = validated_data['title']
        bookmark.description = validated_data['description']
        tag_string = build_tag_string(validated_data['tag_names'], ' ')
        return create_bookmark(bookmark, tag_string, self.context['user'])

    def update(self, instance: Bookmark, validated_data):
        instance.url = validated_data['url']
        instance.title = validated_data['title']
        instance.description = validated_data['description']
        tag_string = build_tag_string(validated_data['tag_names'], ' ')
        return update_bookmark(instance, tag_string, self.context['user'])
