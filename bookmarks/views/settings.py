import logging
import time
from functools import lru_cache

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import prefetch_related_objects
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from rest_framework.authtoken.models import Token

from bookmarks.models import UserProfile, UserProfileForm, FeedToken
from bookmarks.queries import query_bookmarks
from bookmarks.services import exporter, tasks
from bookmarks.services import importer

logger = logging.getLogger(__name__)

try:
    with open("version.txt", "r") as f:
        app_version = f.read().strip("\n")
except Exception as exc:
    logging.exception(exc)
    pass


@login_required
def general(request):
    user = request.user
    profile = user.profile
    if request.method == 'POST':
        favicons_were_enabled = profile.enable_favicons
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            if profile.enable_favicons and not favicons_were_enabled:
                tasks.schedule_bookmarks_without_favicons(request.user)

    else:
        form = UserProfileForm(instance=profile)

    import_success_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import_success')
    import_errors_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import_errors')
    version_info = get_version_info(get_ttl_hash())
    return render(request, 'settings/general.html', {
        'form': form,
        'import_success_message': import_success_message,
        'import_errors_message': import_errors_message,
        'version_info': version_info,
    })


# Cache API call response, for one hour when using get_ttl_hash with default params
@lru_cache(maxsize=1)
def get_version_info(ttl_hash=None):
    latest_version = None
    try:
        latest_version_url = 'https://api.github.com/repos/sissbruecker/linkding/releases/latest'
        response = requests.get(latest_version_url, timeout=5)
        json = response.json()
        if response.status_code == 200 and 'name' in json:
            latest_version = json['name'][1:]
    except requests.exceptions.RequestException:
        pass

    latest_version_info = ''
    if latest_version == app_version:
        latest_version_info = ' (latest)'
    elif latest_version is not None:
        latest_version_info = f' (latest: {latest_version})'

    return f'{app_version}{latest_version_info}'


def get_ttl_hash(seconds=3600):
    """Return the same value within `seconds` time period"""
    return round(time.time() / seconds)


@login_required
def integrations(request):
    application_url = request.build_absolute_uri(reverse('bookmarks:new'))
    api_token = Token.objects.get_or_create(user=request.user)[0]
    feed_token = FeedToken.objects.get_or_create(user=request.user)[0]
    all_feed_url = request.build_absolute_uri(reverse('bookmarks:feeds.all', args=[feed_token.key]))
    unread_feed_url = request.build_absolute_uri(reverse('bookmarks:feeds.unread', args=[feed_token.key]))
    return render(request, 'settings/integrations.html', {
        'application_url': application_url,
        'api_token': api_token.key,
        'all_feed_url': all_feed_url,
        'unread_feed_url': unread_feed_url,
    })


@login_required
def bookmark_import(request):
    import_file = request.FILES.get('import_file')

    if import_file is None:
        messages.error(request, 'Please select a file to import.', 'bookmark_import_errors')
        return HttpResponseRedirect(reverse('bookmarks:settings.general'))

    try:
        content = import_file.read().decode()
        result = importer.import_netscape_html(content, request.user)
        success_msg = str(result.success) + ' bookmarks were successfully imported.'
        messages.success(request, success_msg, 'bookmark_import_success')
        if result.failed > 0:
            err_msg = str(result.failed) + ' bookmarks could not be imported. Please check the logs for more details.'
            messages.error(request, err_msg, 'bookmark_import_errors')
    except:
        logging.exception('Unexpected error during bookmark import')
        messages.error(request, 'An error occurred during bookmark import.', 'bookmark_import_errors')
        pass

    return HttpResponseRedirect(reverse('bookmarks:settings.general'))


@login_required
def bookmark_export(request):
    # noinspection PyBroadException
    try:
        bookmarks = list(query_bookmarks(request.user, ''))
        # Prefetch tags to prevent n+1 queries
        prefetch_related_objects(bookmarks, 'tags')
        file_content = exporter.export_netscape_html(bookmarks)

        response = HttpResponse(content_type='text/plain; charset=UTF-8')
        response['Content-Disposition'] = 'attachment; filename="bookmarks.html"'
        response.write(file_content)

        return response
    except:
        return render(request, 'settings/general.html', {
            'export_error': 'An error occurred during bookmark export.'
        })


def _find_message_with_tag(messages, tag):
    for message in messages:
        if message.extra_tags == tag:
            return message
