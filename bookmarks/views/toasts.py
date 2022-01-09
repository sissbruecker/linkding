from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from bookmarks.models import Toast


@login_required
def acknowledge(request, toast_id: int):
    toast = Toast.objects.get(pk=toast_id, owner=request.user)
    toast.acknowledged = True
    toast.save()

    return_url = request.GET.get('return_url')
    return_url = return_url if return_url else reverse('bookmarks:index')
    return HttpResponseRedirect(return_url)
