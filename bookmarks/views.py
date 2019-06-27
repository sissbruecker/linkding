from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

# Create your views here.
from django.urls import reverse

from .models import Bookmark


def index(request):
    context = {
        'bookmarks': Bookmark.objects.all()
    }
    return render(request, 'bookmarks/index.html', context)


def create(request):
    return HttpResponse('OK')


def detail(request, bookmark_id):
    context = {
        'bookmark': Bookmark.objects.get(bookmark_id)
    }
    return render(request, 'bookmarks/detail.html', context)


def remove(request, bookmark_id: int):
    bookmark = Bookmark.objects.get(pk=bookmark_id)
    bookmark.delete()
    return HttpResponseRedirect(reverse('bookmarks:index'))
