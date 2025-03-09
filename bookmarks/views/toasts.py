from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from bookmarks.utils import get_safe_return_url
from bookmarks.views import access


@login_required
def acknowledge(request):
    toast = access.toast_write(request, request.POST["toast"])
    toast.acknowledged = True
    toast.save()

    return_url = get_safe_return_url(
        request.GET.get("return_url"), reverse("linkding:bookmarks.index")
    )
    return HttpResponseRedirect(return_url)
