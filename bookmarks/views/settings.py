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
from django.utils import timezone

from bookmarks.models import (
    ApiToken,
    Bookmark,
    UserProfileForm,
    FeedToken,
    GlobalSettings,
    GlobalSettingsForm,
)
from bookmarks.services import exporter, tasks
from bookmarks.services import importer
from bookmarks.type_defs import HttpRequest
from bookmarks.utils import app_version
from bookmarks.views import access

logger = logging.getLogger(__name__)


@login_required
def general(request: HttpRequest, status=200, context_overrides=None):
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
def update(request: HttpRequest):
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

    return HttpResponseRedirect(reverse("linkding:settings.general"))


def update_profile(request: HttpRequest):
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

        return HttpResponseRedirect(reverse("linkding:settings.general"))

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
    application_url = request.build_absolute_uri(reverse("linkding:bookmarks.new"))

    api_tokens = ApiToken.objects.filter(user=request.user).order_by("-created")
    api_token_key = request.session.pop("api_token_key", None)
    api_token_name = request.session.pop("api_token_name", None)
    api_success_message = _find_message_with_tag(
        messages.get_messages(request), "api_success_message"
    )

    feed_token = FeedToken.objects.get_or_create(user=request.user)[0]
    all_feed_url = request.build_absolute_uri(
        reverse("linkding:feeds.all", args=[feed_token.key])
    )
    unread_feed_url = request.build_absolute_uri(
        reverse("linkding:feeds.unread", args=[feed_token.key])
    )
    shared_feed_url = request.build_absolute_uri(
        reverse("linkding:feeds.shared", args=[feed_token.key])
    )
    public_shared_feed_url = request.build_absolute_uri(
        reverse("linkding:feeds.public_shared")
    )

    return render(
        request,
        "settings/integrations.html",
        {
            "application_url": application_url,
            "api_tokens": api_tokens,
            "api_token_key": api_token_key,
            "api_token_name": api_token_name,
            "api_success_message": api_success_message,
            "all_feed_url": all_feed_url,
            "unread_feed_url": unread_feed_url,
            "shared_feed_url": shared_feed_url,
            "public_shared_feed_url": public_shared_feed_url,
        },
    )


@login_required
def create_api_token(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            name = "API Token"

        token = ApiToken(user=request.user, name=name)
        token.save()

        request.session["api_token_key"] = token.key
        request.session["api_token_name"] = token.name

        messages.success(
            request,
            f'API token "{token.name}" created successfully',
            "api_success_message",
        )

        return HttpResponseRedirect(reverse("linkding:settings.integrations"))

    return render(request, "settings/create_api_token_modal.html")


@login_required
def delete_api_token(request):
    if request.method == "POST":
        token_id = request.POST.get("token_id")
        token = access.api_token_write(request, token_id)
        token_name = token.name
        token.delete()
        messages.success(
            request,
            f'API token "{token_name}" has been deleted.',
            "api_success_message",
        )

    return HttpResponseRedirect(reverse("linkding:settings.integrations"))


@login_required
def bookmark_import(request: HttpRequest):
    import_file = request.FILES.get("import_file")
    import_options = importer.ImportOptions(
        map_private_flag=request.POST.get("map_private_flag") == "on"
    )

    if import_file is None:
        messages.error(
            request, "Please select a file to import.", "settings_error_message"
        )
        return HttpResponseRedirect(reverse("linkding:settings.general"))

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

    return HttpResponseRedirect(reverse("linkding:settings.general"))


@login_required
def bookmark_export(request: HttpRequest):
    # noinspection PyBroadException
    try:
        bookmarks = Bookmark.objects.filter(owner=request.user)
        # Prefetch tags to prevent n+1 queries
        prefetch_related_objects(bookmarks, "tags")
        file_content = exporter.export_netscape_html(list(bookmarks))

        # Generate filename with current date and time
        current_time = timezone.now()
        filename = current_time.strftime("bookmarks_%Y-%m-%d_%H-%M-%S.html")

        response = HttpResponse(content_type="text/plain; charset=UTF-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
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
