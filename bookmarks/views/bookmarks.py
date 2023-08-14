import urllib.parse
from typing import List

from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db.models import QuerySet, Q, prefetch_related_objects
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkForm, BookmarkFilters, User, UserProfile, Tag, build_tag_string
from bookmarks.services.bookmarks import create_bookmark, update_bookmark, archive_bookmark, archive_bookmarks, \
    unarchive_bookmark, unarchive_bookmarks, delete_bookmarks, tag_bookmarks, untag_bookmarks
from bookmarks.utils import get_safe_return_url

_default_page_size = 30


@login_required
def index(request):
    filters = BookmarkFilters(request)
    query_set = queries.query_bookmarks(request.user, request.user_profile, filters.query)
    tags = queries.query_bookmark_tags(request.user, request.user_profile, filters.query)
    base_url = reverse('bookmarks:index')
    context = get_bookmark_view_context(request, filters, query_set, tags, base_url)
    return render(request, 'bookmarks/index.html', context)


@login_required
def archived(request):
    filters = BookmarkFilters(request)
    query_set = queries.query_archived_bookmarks(request.user, request.user_profile, filters.query)
    tags = queries.query_archived_bookmark_tags(request.user, request.user_profile, filters.query)
    base_url = reverse('bookmarks:archived')
    context = get_bookmark_view_context(request, filters, query_set, tags, base_url)
    return render(request, 'bookmarks/archive.html', context)


def shared(request):
    filters = BookmarkFilters(request)
    user = User.objects.filter(username=filters.user).first()
    public_only = not request.user.is_authenticated
    query_set = queries.query_shared_bookmarks(user, request.user_profile, filters.query, public_only)
    tags = queries.query_shared_bookmark_tags(user, request.user_profile, filters.query, public_only)
    users = queries.query_shared_bookmark_users(request.user_profile, filters.query, public_only)
    base_url = reverse('bookmarks:shared')
    context = get_bookmark_view_context(request, filters, query_set, tags, base_url)
    context['users'] = users
    return render(request, 'bookmarks/shared.html', context)


def _get_selected_tags(tags: List[Tag], query_string: str, profile: UserProfile):
    parsed_query = queries.parse_query_string(query_string)
    tag_names = parsed_query['tag_names']
    if profile.tag_search == UserProfile.TAG_SEARCH_LAX:
        tag_names = tag_names + parsed_query['search_terms']
    tag_names = [tag_name.lower() for tag_name in tag_names]

    return [tag for tag in tags if tag.name.lower() in tag_names]


def get_bookmark_view_context(request: WSGIRequest,
                              filters: BookmarkFilters,
                              query_set: QuerySet[Bookmark],
                              tags: QuerySet[Tag],
                              base_url: str):
    page = request.GET.get('page')
    paginator = Paginator(query_set, _default_page_size)
    bookmarks = paginator.get_page(page)
    tags = list(tags)
    selected_tags = _get_selected_tags(tags, filters.query, request.user_profile)
    # Prefetch related objects, this avoids n+1 queries when accessing fields in templates
    prefetch_related_objects(bookmarks.object_list, 'owner', 'tags')
    return_url = generate_return_url(base_url, page, filters)
    link_target = request.user_profile.bookmark_link_target

    if request.GET.get('tag'):
        mod = request.GET.copy()
        mod.pop('tag')
        request.GET = mod

    return {
        'bookmarks': bookmarks,
        'tags': tags,
        'selected_tags': selected_tags,
        'filters': filters,
        'empty': paginator.count == 0,
        'return_url': return_url,
        'link_target': link_target,
    }


def generate_return_url(base_url: str, page: int, filters: BookmarkFilters):
    url_query = {}
    if filters.query:
        url_query['q'] = filters.query
    if filters.user:
        url_query['user'] = filters.user
    if page is not None:
        url_query['page'] = page
    url_params = urllib.parse.urlencode(url_query)
    return_url = base_url if url_params == '' else base_url + '?' + url_params
    return urllib.parse.quote_plus(return_url)


def convert_tag_string(tag_string: str):
    # Tag strings coming from inputs are space-separated, however services.bookmarks functions expect comma-separated
    # strings
    return tag_string.replace(' ', ',')


@login_required
def new(request):
    initial_url = request.GET.get('url')
    initial_title = request.GET.get('title')
    initial_description = request.GET.get('description')
    initial_auto_close = 'auto_close' in request.GET

    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        auto_close = form.data['auto_close']
        if form.is_valid():
            current_user = request.user
            tag_string = convert_tag_string(form.data['tag_string'])
            create_bookmark(form.save(commit=False), tag_string, current_user)
            if auto_close:
                return HttpResponseRedirect(reverse('bookmarks:close'))
            else:
                return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm()
        if initial_url:
            form.initial['url'] = initial_url
        if initial_title:
            form.initial['title'] = initial_title
        if initial_description:
            form.initial['description'] = initial_description
        if initial_auto_close:
            form.initial['auto_close'] = 'true'

    context = {
        'form': form,
        'auto_close': initial_auto_close,
        'return_url': reverse('bookmarks:index')
    }

    return render(request, 'bookmarks/new.html', context)


@login_required
def edit(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')
    return_url = get_safe_return_url(request.GET.get('return_url'), reverse('bookmarks:index'))

    if request.method == 'POST':
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            tag_string = convert_tag_string(form.data['tag_string'])
            update_bookmark(form.save(commit=False), tag_string, request.user)
            return HttpResponseRedirect(return_url)
    else:
        form = BookmarkForm(instance=bookmark)

    form.initial['tag_string'] = build_tag_string(bookmark.tag_names, ' ')

    context = {
        'form': form,
        'bookmark_id': bookmark_id,
        'return_url': return_url
    }

    return render(request, 'bookmarks/edit.html', context)


def remove(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    bookmark.delete()


def archive(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    archive_bookmark(bookmark)


def unarchive(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    unarchive_bookmark(bookmark)


def mark_as_read(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    bookmark.unread = False
    bookmark.save()


@login_required
def action(request):
    # Determine action
    if 'archive' in request.POST:
        archive(request, request.POST['archive'])
    if 'unarchive' in request.POST:
        unarchive(request, request.POST['unarchive'])
    if 'remove' in request.POST:
        remove(request, request.POST['remove'])
    if 'mark_as_read' in request.POST:
        mark_as_read(request, request.POST['mark_as_read'])
    if 'bulk_archive' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        archive_bookmarks(bookmark_ids, request.user)
    if 'bulk_unarchive' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        unarchive_bookmarks(bookmark_ids, request.user)
    if 'bulk_delete' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        delete_bookmarks(bookmark_ids, request.user)
    if 'bulk_tag' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        tag_string = convert_tag_string(request.POST['bulk_tag_string'])
        tag_bookmarks(bookmark_ids, tag_string, request.user)
    if 'bulk_untag' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        tag_string = convert_tag_string(request.POST['bulk_tag_string'])
        untag_bookmarks(bookmark_ids, tag_string, request.user)

    return_url = get_safe_return_url(request.GET.get('return_url'), reverse('bookmarks:index'))
    return HttpResponseRedirect(return_url)


@login_required
def close(request):
    return render(request, 'bookmarks/close.html')
