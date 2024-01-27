from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse

from bookmarks.models import Toast
from bookmarks.utils import get_safe_return_url


@login_required
def acknowledge(request):
    toast_id = request.POST["toast"]
    try:
        toast = Toast.objects.get(pk=toast_id, owner=request.user)
    except Toast.DoesNotExist:
        raise Http404("Toast does not exist")
    toast.acknowledged = True
    toast.save()

    return_url = get_safe_return_url(
        request.GET.get("return_url"), reverse("bookmarks:index")
    )
    return HttpResponseRedirect(return_url)
