import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from rest_framework.authtoken.models import Token

from bookmarks.queries import query_bookmarks
from bookmarks.services.exporter import export_netscape_html
from bookmarks.services.importer import import_netscape_html

logger = logging.getLogger(__name__)


@login_required
def index(request):
    import_success_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import_success')
    import_errors_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import_errors')
    api_token = Token.objects.get_or_create(user=request.user)[0]
    return render(request, 'settings/index.html', {
        'import_success_message': import_success_message,
        'import_errors_message': import_errors_message,
        'api_token': api_token.key
    })


@login_required
def bookmark_import(request):
    import_file = request.FILES.get('import_file')

    if import_file is None:
        messages.error(request, 'Please select a file to import.', 'bookmark_import_errors')
        return HttpResponseRedirect(reverse('bookmarks:settings.index'))

    try:
        content = import_file.read().decode()
        result = import_netscape_html(content, request.user)
        success_msg = str(result.success) + ' bookmarks were successfully imported.'
        messages.success(request, success_msg, 'bookmark_import_success')
        if result.failed > 0:
            err_msg = str(result.failed) + ' bookmarks could not be imported. Please check the logs for more details.'
            messages.error(request, err_msg, 'bookmark_import_errors')
    except:
        logging.exception('Unexpected error during bookmark import')
        messages.error(request, 'An error occurred during bookmark import.', 'bookmark_import_errors')
        pass

    return HttpResponseRedirect(reverse('bookmarks:settings.index'))


@login_required
def bookmark_export(request):
    # noinspection PyBroadException
    try:
        bookmarks = query_bookmarks(request.user, '')
        file_content = export_netscape_html(bookmarks)

        response = HttpResponse(content_type='text/plain; charset=UTF-8')
        response['Content-Disposition'] = 'attachment; filename="bookmarks.html"'
        response.write(file_content)

        return response
    except:
        return render(request, 'settings/index.html', {
            'export_error': 'An error occurred during bookmark export.'
        })


def _find_message_with_tag(messages, tag):
    for message in messages:
        if message.extra_tags == tag:
            return message
