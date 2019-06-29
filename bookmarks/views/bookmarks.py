from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkForm
from bookmarks.services.bookmarks import create_bookmark, update_bookmark

_default_page_size = 30


def index(request):
    page = request.GET.get('page')
    query_string = request.GET.get('q')
    query_set = queries.query_bookmarks(request.user, query_string)
    paginator = Paginator(query_set, _default_page_size)
    bookmarks = paginator.get_page(page)

    context = {
        'bookmarks': bookmarks,
        'query': query_string if query_string else '',
    }
    return render(request, 'bookmarks/index.html', context)


def new(request):
    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        if form.is_valid():
            bookmark = form.save(commit=False)
            current_user = request.user
            create_bookmark(bookmark, current_user)
            return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm()

    return render(request, 'bookmarks/new.html', {'form': form})


def edit(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    if request.method == 'POST':
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            bookmark = form.save(commit=False)
            update_bookmark(bookmark)
            return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm(instance=bookmark)

    return render(request, 'bookmarks/edit.html', {'form': form, 'bookmark_id': bookmark_id})


def remove(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    bookmark.delete()
    return HttpResponseRedirect(reverse('bookmarks:index'))
