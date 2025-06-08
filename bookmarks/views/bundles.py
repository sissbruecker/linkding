from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from bookmarks.views.contexts import ActiveBookmarkListContext
from bookmarks.models import BookmarkBundle, BookmarkBundleForm, BookmarkSearch
from bookmarks.views import access


@login_required
def index(request: HttpRequest):
    if request.method == "POST":
        # Handle bundle deletion
        remove_bundle_id = request.POST.get("remove_bundle")
        if remove_bundle_id:
            bundle = access.bundle_write(request, remove_bundle_id)
            bundle_name = bundle.name
            bundle.delete()
            messages.success(request, f"Bundle '{bundle_name}' removed successfully.")
            return HttpResponseRedirect(reverse("linkding:bundles.index"))

    bundles = BookmarkBundle.objects.filter(owner=request.user).order_by("name")
    context = {"bundles": bundles}
    return render(request, "bundles/index.html", context)


def _handle_edit(request: HttpRequest, template: str, bundle: BookmarkBundle = None):
    form_data = request.POST if request.method == "POST" else None
    form = BookmarkBundleForm(form_data, instance=bundle)

    if request.method == "POST":
        if form.is_valid():
            instance = form.save(commit=False)
            instance.owner = request.user
            instance.save()
            messages.success(request, "Bundle saved successfully.")
            return HttpResponseRedirect(reverse("linkding:bundles.index"))

    status = 422 if request.method == "POST" and not form.is_valid() else 200
    context = {"form": form, "bundle": bundle}

    return render(request, template, context, status=status)


@login_required
def new(request: HttpRequest):
    return _handle_edit(request, "bundles/new.html")


@login_required
def edit(request: HttpRequest, bundle_id: int):
    bundle = access.bundle_write(request, bundle_id)

    return _handle_edit(request, "bundles/edit.html", bundle)


@login_required
def preview(request: HttpRequest):
    form_data = request.GET.copy()
    form_data["name"] = "Preview Bundle"  # Set dummy name for form validation
    form = BookmarkBundleForm(form_data)
    preview_bundle = form.save(commit=False)
    preview_bundle.owner = request.user
    bookmark_list = ActiveBookmarkListContext(request, preview_bundle)
    bookmark_list.is_preview = True
    context = {"bookmark_list": bookmark_list}
    return render(request, "bundles/preview.html", context)
