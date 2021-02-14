from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from bookmarks import queries
from bookmarks.api.serializers import BookmarkSerializer, TagSerializer
from bookmarks.models import Bookmark, Tag


class BookmarkViewSet(viewsets.GenericViewSet,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin):
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        user = self.request.user
        # For list action, use query set that applies search and tag projections
        if self.action == 'list':
            query_string = self.request.GET.get('q')
            return queries.query_bookmarks(user, query_string)

        # For single entity actions use default query set without projections
        return Bookmark.objects.all().filter(owner=user)

    def get_serializer_context(self):
        return {'user': self.request.user}

    @action(methods=['get'], detail=False)
    def archived(self, request):
        user = request.user
        query_string = request.GET.get('q')
        query_set = queries.query_archived_bookmarks(user, query_string)
        page = self.paginate_queryset(query_set)
        serializer = self.get_serializer_class()
        data = serializer(page, many=True).data
        return self.get_paginated_response(data)


class TagViewSet(viewsets.GenericViewSet,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.CreateModelMixin):
    serializer_class = TagSerializer

    def get_queryset(self):
        user = self.request.user
        return Tag.objects.all().filter(owner=user)

    def get_serializer_context(self):
        return {'user': self.request.user}


router = DefaultRouter()
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')
router.register(r'tags', TagViewSet, basename='tag')
