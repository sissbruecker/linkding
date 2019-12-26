from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from bookmarks.queries import query_bookmarks
from bookmarks.services.exporter import export_netscape_html
from bookmarks.services.importer import import_netscape_html


@login_required
def index(request):
    import_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import')
    return render(request, 'settings/index.html', {
        'import_message': import_message
    })


@login_required
def bookmark_import(request):
    try:
        import_file = request.FILES.get('import_file')
        content = import_file.read()
        import_netscape_html(content, request.user)
        messages.success(request, 'Bookmarks were successfully imported.', 'bookmark_import')
    except Exception:
        messages.error(request, 'An error occurred during bookmark import.', 'bookmark_import')
        pass

    return HttpResponseRedirect(reverse('bookmarks:settings.index'))


@login_required
def bookmark_export(request):
    try:
        bookmarks = query_bookmarks(request.user, '')
        file_content = export_netscape_html(bookmarks)

        response = HttpResponse(content_type='text/plain; charset=UTF-8')
        response['Content-Disposition'] = 'attachment; filename="bookmarks.html"'
        response.write(file_content)

        return response
    except Exception:
        return render(request, 'settings/index.html', {
            'export_error': 'An error occurred during bookmark export.'
        })


def _find_message_with_tag(messages, tag):
    for message in messages:
        if message.extra_tags == tag:
            return message
