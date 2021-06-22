import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from rest_framework.authtoken.models import Token

from bookmarks.models import UserProfileForm
from bookmarks.queries import query_bookmarks
from bookmarks.services import exporter
from bookmarks.services import importer

logger = logging.getLogger(__name__)


@login_required
def general(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
    else:
        form = UserProfileForm(instance=request.user.profile)

    import_success_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import_success')
    import_errors_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import_errors')
    return render(request, 'settings/general.html', {
        'form': form,
        'import_success_message': import_success_message,
        'import_errors_message': import_errors_message,
    })


def about(request):
    app_version = _get_app_version()
    return render(request, 'settings/about.html', {
        'version': app_version
    })


@login_required
def integrations(request):
    application_url = request.build_absolute_uri("/bookmarks/new")
    return render(request, 'settings/integrations.html', {
        'application_url': application_url,
    })


@login_required
def api(request):
    api_token = Token.objects.get_or_create(user=request.user)[0]
    return render(request, 'settings/api.html', {
        'api_token': api_token.key
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
        bookmarks = query_bookmarks(request.user, '')
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

def _get_app_version():
    try:
        with open("version.txt", "r") as f:
            return f.read().strip("\n")
    except Exception as exc: 
        logging.exception(exc)
        pass
