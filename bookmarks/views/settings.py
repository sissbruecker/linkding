from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from bookmarks.services.importer import import_netscape_html


@login_required
def settings_index(request):
    import_message = _find_message_with_tag(messages.get_messages(request), 'bookmark_import')
    return render(request, 'settings/index.html', {
        'import_message': import_message
    })


@login_required
def settings_bookmark_import(request):
    try:
        import_file = request.FILES.get('import_file')
        content = import_file.read()
        import_netscape_html(content, request.user)
        messages.success(request, 'Bookmarks were successfully imported.', 'bookmark_import')
    except():
        messages.error(request, 'An error occurred during bookmark import.', 'bookmark_import')
        pass

    return HttpResponseRedirect(reverse('bookmarks:settings_index'))


def _find_message_with_tag(messages, tag):
    for message in messages:
        if message.extra_tags == tag:
            return message
