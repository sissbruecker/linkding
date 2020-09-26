from rest_framework import viewsets, mixins
from rest_framework.routers import DefaultRouter

from bookmarks import queries
from bookmarks.api.serializers import BookmarkSerializer


class BookmarkViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        user = self.request.user
        query_string = self.request.GET.get('q')
        return queries.query_bookmarks(user, query_string)


router = DefaultRouter()
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')