import logging
import time
from functools import lru_cache

import requests
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import prefetch_related_objects
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from rest_framework.authtoken.models import Token

from bookmarks.models import (
    Bookmark,
    UserProfileForm,
    FeedToken,
    GlobalSettings,
    GlobalSettingsForm,
)
from bookmarks.services import exporter, tasks
from bookmarks.services import importer
from bookmarks.utils import app_version

logger = logging.getLogger(__name__)


@login_required
def general(request, status=200, context_overrides=None):
    enable_refresh_favicons = django_settings.LD_ENABLE_REFRESH_FAVICONS
    has_snapshot_support = django_settings.LD_ENABLE_SNAPSHOTS
    success_message = _find_message_with_tag(
        messages.get_messages(request), "settings_success_message"
    )
    error_message = _find_message_with_tag(
        messages.get_messages(request), "settings_error_message"
    )
    version_info = get_version_info(get_ttl_hash())

    profile_form = UserProfileForm(instance=request.user_profile)
    global_settings_form = None
    if request.user.is_superuser:
        global_settings_form = GlobalSettingsForm(instance=GlobalSettings.get())

    if context_overrides is None:
        context_overrides = {}

    return render(
        request,
        "settings/general.html",
        {
            "form": profile_form,
            "global_settings_form": global_settings_form,
            "enable_refresh_favicons": enable_refresh_favicons,
            "has_snapshot_support": has_snapshot_support,
            "success_message": success_message,
            "error_message": error_message,
            "version_info": version_info,
            **context_overrides,
        },
        status=status,
    )


@login_required
def update(request):
    if request.method == "POST":
        if "update_profile" in request.POST:
            return update_profile(request)
        if "update_global_settings" in request.POST:
            update_global_settings(request)
            messages.success(
                request, "Global settings updated", "settings_success_message"
            )
        if "refresh_favicons" in request.POST:
            tasks.schedule_refresh_favicons(request.user)
            messages.success(
                request,
                "Scheduled favicon update. This may take a while...",
                "settings_success_message",
            )
        if "create_missing_html_snapshots" in request.POST:
            count = tasks.create_missing_html_snapshots(request.user)
            if count > 0:
                messages.success(
                    request,
                    f"Queued {count} missing snapshots. This may take a while...",
                    "settings_success_message",
                )
            else:
                messages.success(
                    request, "No missing snapshots found.", "settings_success_message"
                )

    return HttpResponseRedirect(reverse("bookmarks:settings.general"))


def update_profile(request):
    user = request.user
    profile = user.profile
    favicons_were_enabled = profile.enable_favicons
    previews_were_enabled = profile.enable_preview_images
    form = UserProfileForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, "Profile updated", "settings_success_message")
        # Load missing favicons if the feature was just enabled
        if profile.enable_favicons and not favicons_were_enabled:
            tasks.schedule_bookmarks_without_favicons(request.user)
        # Load missing preview images if the feature was just enabled
        if profile.enable_preview_images and not previews_were_enabled:
            tasks.schedule_bookmarks_without_previews(request.user)

        return HttpResponseRedirect(reverse("bookmarks:settings.general"))

    messages.error(
        request,
        "Profile update failed, check the form below for errors",
        "settings_error_message",
    )
    return general(request, 422, {"form": form})


def update_global_settings(request):
    user = request.user
    if not user.is_superuser:
        raise PermissionDenied()

    form = GlobalSettingsForm(request.POST, instance=GlobalSettings.get())
    if form.is_valid():
        form.save()
    return form


# Cache API call response, for one hour when using get_ttl_hash with default params
@lru_cache(maxsize=1)
def get_version_info(ttl_hash=None):
    latest_version = None
    try:
        latest_version_url = (
            "https://api.github.com/repos/sissbruecker/linkding/releases/latest"
        )
        response = requests.get(latest_version_url, timeout=5)
        json = response.json()
        if response.status_code == 200 and "name" in json:
            latest_version = json["name"][1:]
    except requests.exceptions.RequestException:
        pass

    latest_version_info = ""
    if latest_version == app_version:
        latest_version_info = " (latest)"
    elif latest_version is not None:
        latest_version_info = f" (latest: {latest_version})"

    return f"{app_version}{latest_version_info}"


def get_ttl_hash(seconds=3600):
    """Return the same value within `seconds` time period"""
    return round(time.time() / seconds)


@login_required
def integrations(request):
    application_url = request.build_absolute_uri(reverse("bookmarks:new"))
    api_token = Token.objects.get_or_create(user=request.user)[0]
    feed_token = FeedToken.objects.get_or_create(user=request.user)[0]
    all_feed_url = request.build_absolute_uri(
        reverse("bookmarks:feeds.all", args=[feed_token.key])
    )
    unread_feed_url = request.build_absolute_uri(
        reverse("bookmarks:feeds.unread", args=[feed_token.key])
    )
    shared_feed_url = request.build_absolute_uri(
        reverse("bookmarks:feeds.shared", args=[feed_token.key])
    )
    public_shared_feed_url = request.build_absolute_uri(
        reverse("bookmarks:feeds.public_shared")
    )
    return render(
        request,
        "settings/integrations.html",
        {
            "application_url": application_url,
            "api_token": api_token.key,
            "all_feed_url": all_feed_url,
            "unread_feed_url": unread_feed_url,
            "shared_feed_url": shared_feed_url,
            "public_shared_feed_url": public_shared_feed_url,
        },
    )


@login_required
def bookmark_import(request):
    import_file = request.FILES.get("import_file")
    import_options = importer.ImportOptions(
        map_private_flag=request.POST.get("map_private_flag") == "on"
    )

    if import_file is None:
        messages.error(
            request, "Please select a file to import.", "settings_error_message"
        )
        return HttpResponseRedirect(reverse("bookmarks:settings.general"))

    try:
        content = import_file.read().decode()
        result = importer.import_netscape_html(content, request.user, import_options)
        success_msg = str(result.success) + " bookmarks were successfully imported."
        messages.success(request, success_msg, "settings_success_message")
        if result.failed > 0:
            err_msg = (
                str(result.failed)
                + " bookmarks could not be imported. Please check the logs for more details."
            )
            messages.error(request, err_msg, "settings_error_message")
    except:
        logging.exception("Unexpected error during bookmark import")
        messages.error(
            request,
            "An error occurred during bookmark import.",
            "settings_error_message",
        )

    return HttpResponseRedirect(reverse("bookmarks:settings.general"))


@login_required
def bookmark_export(request):
    # noinspection PyBroadException
    try:
        bookmarks = Bookmark.objects.filter(owner=request.user)
        # Prefetch tags to prevent n+1 queries
        prefetch_related_objects(bookmarks, "tags")
        file_content = exporter.export_netscape_html(bookmarks)

        response = HttpResponse(content_type="text/plain; charset=UTF-8")
        response["Content-Disposition"] = 'attachment; filename="bookmarks.html"'
        response.write(file_content)

        return response
    except:
        return render(
            request,
            "settings/general.html",
            {"export_error": "An error occurred during bookmark export."},
        )


def _find_message_with_tag(messages, tag):
    for message in messages:
        if message.extra_tags == tag:
            return message
