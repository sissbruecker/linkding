import urllib.parse

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkForm, build_tag_string
from bookmarks.services.bookmarks import create_bookmark, update_bookmark, archive_bookmark, unarchive_bookmark

_default_page_size = 30


@login_required
def index(request):
    query_string = request.GET.get('q')
    query_set = queries.query_bookmarks(request.user, query_string)
    tags = queries.query_bookmark_tags(request.user, query_string)
    base_url = reverse('bookmarks:index')
    context = get_bookmark_view_context(request, query_set, tags, base_url)
    return render(request, 'bookmarks/index.html', context)


@login_required
def archived(request):
    query_string = request.GET.get('q')
    query_set = queries.query_archived_bookmarks(request.user, query_string)
    tags = queries.query_archived_bookmark_tags(request.user, query_string)
    base_url = reverse('bookmarks:archived')
    context = get_bookmark_view_context(request, query_set, tags, base_url)
    return render(request, 'bookmarks/archive.html', context)


def get_bookmark_view_context(request, query_set, tags, base_url):
    page = request.GET.get('page')
    query_string = request.GET.get('q')
    paginator = Paginator(query_set, _default_page_size)
    bookmarks = paginator.get_page(page)
    tag_names = [tag.name for tag in tags]
    tags_string = build_tag_string(tag_names, ' ')
    return_url = generate_return_url(base_url, page, query_string)

    if request.GET.get('tag'):
        mod = request.GET.copy()
        mod.pop('tag')
        request.GET = mod

    return {
        'bookmarks': bookmarks,
        'tags': tags,
        'tags_string': tags_string,
        'query': query_string if query_string else '',
        'empty': paginator.count == 0,
        'return_url': return_url
    }


def generate_return_url(base_url, page, query_string):
    url_query = {}
    if query_string is not None:
        url_query['q'] = query_string
    if page is not None:
        url_query['page'] = page
    url_params = urllib.parse.urlencode(url_query)
    return_url = base_url if url_params == '' else base_url + '?' + url_params
    return urllib.parse.quote_plus(return_url)


@login_required
def new(request):
    initial_url = request.GET.get('url')
    initial_auto_close = 'auto_close' in request.GET

    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        auto_close = form.data['auto_close']
        if form.is_valid():
            current_user = request.user
            create_bookmark(form.save(commit=False), form.data['tag_string'], current_user)
            if auto_close:
                return HttpResponseRedirect(reverse('bookmarks:close'))
            else:
                return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm()
        if initial_url:
            form.initial['url'] = initial_url
        if initial_auto_close:
            form.initial['auto_close'] = 'true'

    all_tags = queries.get_user_tags(request.user)
    context = {
        'form': form,
        'auto_close': initial_auto_close,
        'all_tags': all_tags,
        'return_url': reverse('bookmarks:index')
    }

    return render(request, 'bookmarks/new.html', context)


@login_required
def edit(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)

    if request.method == 'POST':
        form = BookmarkForm(request.POST, instance=bookmark)
        return_url = form.data['return_url']
        if form.is_valid():
            update_bookmark(form.save(commit=False), form.data['tag_string'], request.user)
            return HttpResponseRedirect(return_url)
    else:
        return_url = request.GET.get('return_url')
        form = BookmarkForm(instance=bookmark)

    return_url = return_url if return_url else reverse('bookmarks:index')

    form.initial['tag_string'] = build_tag_string(bookmark.tag_names, ' ')
    form.initial['return_url'] = return_url
    all_tags = queries.get_user_tags(request.user)

    context = {
        'form': form,
        'bookmark_id': bookmark_id,
        'all_tags': all_tags,
        'return_url': return_url
    }

    return render(request, 'bookmarks/edit.html', context)


@login_required
def remove(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    bookmark.delete()
    return_url = request.GET.get('return_url')
    return_url = return_url if return_url else reverse('bookmarks:index')
    return HttpResponseRedirect(return_url)


@login_required
def archive(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    archive_bookmark(bookmark)
    return_url = request.GET.get('return_url')
    return_url = return_url if return_url else reverse('bookmarks:index')
    return HttpResponseRedirect(return_url)


@login_required
def unarchive(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    unarchive_bookmark(bookmark)
    return_url = request.GET.get('return_url')
    return_url = return_url if return_url else reverse('bookmarks:archived')
    return HttpResponseRedirect(return_url)


@login_required
def bookmarklet(request):
    return render(request, 'bookmarks/bookmarklet.html', {
        'application_url': request.build_absolute_uri("/bookmarks/new")
    })


@login_required
def close(request):
    return render(request, 'bookmarks/close.html')
