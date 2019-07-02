from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkForm, build_tag_string
from bookmarks.services.bookmarks import create_bookmark, update_bookmark

_default_page_size = 30


@login_required
def index(request):
    page = request.GET.get('page')
    query_string = request.GET.get('q')
    query_set = queries.query_bookmarks(request.user, query_string)
    paginator = Paginator(query_set, _default_page_size)
    bookmarks = paginator.get_page(page)
    tags = queries.query_tags(request.user, query_string)

    if request.GET.get('tag'):
        mod = request.GET.copy()
        mod.pop('tag')
        request.GET = mod

    context = {
        'bookmarks': bookmarks,
        'tags': tags,
        'query': query_string if query_string else '',
    }
    return render(request, 'bookmarks/index.html', context)


@login_required
def new(request):
    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        if form.is_valid():
            current_user = request.user
            create_bookmark(form, current_user)
            return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm()

    return render(request, 'bookmarks/new.html', {'form': form})


@login_required
def edit(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    if request.method == 'POST':
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            update_bookmark(form, request.user)
            return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm(instance=bookmark)

    form.initial['tag_string'] = build_tag_string(bookmark.tag_names, ' ')
    return render(request, 'bookmarks/edit.html', {'form': form, 'bookmark_id': bookmark_id})


@login_required
def remove(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    bookmark.delete()
    return HttpResponseRedirect(reverse('bookmarks:index'))
