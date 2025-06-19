from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from bookmarks.models import BookmarkBundle, BookmarkBundleForm, BookmarkSearch
from bookmarks.views import access
from bookmarks.views.contexts import ActiveBookmarkListContext


@login_required
def index(request: HttpRequest):
    bundles = BookmarkBundle.objects.filter(owner=request.user).order_by("order")
    context = {"bundles": bundles}
    return render(request, "bundles/index.html", context)


@login_required
def action(request: HttpRequest):
    if "remove_bundle" in request.POST:
        remove_bundle_id = request.POST.get("remove_bundle")
        bundle = access.bundle_write(request, remove_bundle_id)
        bundle_name = bundle.name
        bundle.delete()
        messages.success(request, f"Bundle '{bundle_name}' removed successfully.")

    elif "move_bundle" in request.POST:
        bundle_id = request.POST.get("move_bundle")
        move_position = int(request.POST.get("move_position"))
        bundle_to_move = access.bundle_write(request, bundle_id)
        user_bundles = list(
            BookmarkBundle.objects.filter(owner=request.user).order_by("order")
        )

        if move_position != user_bundles.index(bundle_to_move):
            user_bundles.remove(bundle_to_move)
            user_bundles.insert(move_position, bundle_to_move)
            for bundle_index, bundle in enumerate(user_bundles):
                bundle.order = bundle_index

            BookmarkBundle.objects.bulk_update(user_bundles, ["order"])

    return HttpResponseRedirect(reverse("linkding:bundles.index"))


def _handle_edit(request: HttpRequest, template: str, bundle: BookmarkBundle = None):
    form_data = request.POST if request.method == "POST" else None
    form = BookmarkBundleForm(form_data, instance=bundle)

    if request.method == "POST":
        if form.is_valid():
            instance = form.save(commit=False)
            instance.owner = request.user

            if bundle is None:  # New bundle
                max_order_result = BookmarkBundle.objects.filter(
                    owner=request.user
                ).aggregate(Max("order", default=-1))
                instance.order = max_order_result["order__max"] + 1

            instance.save()
            messages.success(request, "Bundle saved successfully.")
            return HttpResponseRedirect(reverse("linkding:bundles.index"))

    status = 422 if request.method == "POST" and not form.is_valid() else 200
    bookmark_list = _get_bookmark_list_preview(request, bundle)
    context = {"form": form, "bundle": bundle, "bookmark_list": bookmark_list}

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
    bookmark_list = _get_bookmark_list_preview(request)
    context = {"bookmark_list": bookmark_list}
    return render(request, "bundles/preview.html", context)


def _get_bookmark_list_preview(
    request: HttpRequest, bundle: BookmarkBundle | None = None
):
    if request.method == "GET" and bundle:
        preview_bundle = bundle
    else:
        form_data = (
            request.POST.copy() if request.method == "POST" else request.GET.copy()
        )
        form_data["name"] = "Preview Bundle"  # Set dummy name for form validation
        form = BookmarkBundleForm(form_data)
        preview_bundle = form.save(commit=False)

    search = BookmarkSearch(bundle=preview_bundle)
    bookmark_list = ActiveBookmarkListContext(request, search)
    bookmark_list.is_preview = True
    return bookmark_list
