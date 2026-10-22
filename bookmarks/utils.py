import datetime
import logging
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.utils.translation import ngettext

try:
    with open("version.txt") as f:
        app_version = f.read().strip("\n")
except Exception as exc:
    logging.exception(exc)
    app_version = ""


def unique(elements, key):
    return list({key(element): element for element in elements}.values())


weekday_names = {
    1: _lazy("Monday"),
    2: _lazy("Tuesday"),
    3: _lazy("Wednesday"),
    4: _lazy("Thursday"),
    5: _lazy("Friday"),
    6: _lazy("Saturday"),
    7: _lazy("Sunday"),
}


@dataclass
class DateDelta:
    years: int
    months: int
    weeks: int


def _calculate_date_delta(
    now: datetime.datetime, value: datetime.datetime
) -> DateDelta:
    """Calculate the difference between two datetimes in years, months, and weeks."""
    # Full calendar years
    years = now.year - value.year
    if (now.month, now.day) < (value.month, value.day):
        years -= 1

    # Full calendar months
    months = (now.year - value.year) * 12 + (now.month - value.month)
    if now.day < value.day:
        months -= 1

    # Weeks from total days
    weeks = (now - value).days // 7

    return DateDelta(years=max(0, years), months=max(0, months), weeks=max(0, weeks))


def humanize_absolute_date(
    value: datetime.datetime, now: datetime.datetime | None = None
):
    if not now:
        now = timezone.now()
    delta = _calculate_date_delta(now, value)
    yesterday = now - datetime.timedelta(days=1)

    is_older_than_a_week = delta.years > 0 or delta.months > 0 or delta.weeks > 0

    if is_older_than_a_week:
        return formats.date_format(value, "SHORT_DATE_FORMAT")
    elif value.day == now.day:
        return _("Today")
    elif value.day == yesterday.day:
        return _("Yesterday")
    else:
        return str(weekday_names[value.isoweekday()])


def humanize_relative_date(
    value: datetime.datetime, now: datetime.datetime | None = None
):
    if not now:
        now = timezone.now()
    delta = _calculate_date_delta(now, value)

    if delta.years > 0:
        return ngettext(
            "%(count)s year ago", "%(count)s years ago", delta.years
        ) % {"count": delta.years}
    elif delta.months > 0:
        return ngettext(
            "%(count)s month ago", "%(count)s months ago", delta.months
        ) % {"count": delta.months}
    elif delta.weeks > 0:
        return ngettext(
            "%(count)s week ago", "%(count)s weeks ago", delta.weeks
        ) % {"count": delta.weeks}
    else:
        yesterday = now - datetime.timedelta(days=1)
        if value.day == now.day:
            return _("Today")
        elif value.day == yesterday.day:
            return _("Yesterday")
        else:
            return str(weekday_names[value.isoweekday()])


def parse_timestamp(value: str):
    """
    Parses a string timestamp into a datetime value
    First tries to parse the timestamp as milliseconds.
    If that fails with an error indicating that the timestamp exceeds the maximum,
    it tries to parse the timestamp as microseconds, and then as nanoseconds
    :param value:
    :return:
    """
    try:
        timestamp = int(value)
    except ValueError:
        raise ValueError(f"{value} is not a valid timestamp") from None

    try:
        return datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
    except (OverflowError, ValueError, OSError):
        pass

    # Value exceeds the max. allowed timestamp
    # Try parsing as microseconds
    try:
        return datetime.datetime.fromtimestamp(timestamp / 1000, datetime.UTC)
    except (OverflowError, ValueError, OSError):
        pass

    # Value exceeds the max. allowed timestamp
    # Try parsing as nanoseconds
    try:
        return datetime.datetime.fromtimestamp(timestamp / 1000000, datetime.UTC)
    except (OverflowError, ValueError, OSError):
        pass

    # Timestamp is out of range
    raise ValueError(f"{value} exceeds maximum value for a timestamp")


def get_safe_return_url(return_url: str, fallback_url: str):
    # Use fallback if URL is none or URL is not on same domain
    if not return_url or not re.match(r"^/[a-z]+", return_url):
        return fallback_url
    return return_url


def redirect_with_query(request, redirect_url):
    query_string = urllib.parse.urlencode(request.GET)
    if query_string:
        redirect_url += "?" + query_string

    return HttpResponseRedirect(redirect_url)


def generate_username(email, claims):
    # taken from mozilla-django-oidc docs :)
    # Using Python 3 and Django 1.11+, usernames can contain alphanumeric
    # (ascii and unicode), _, @, +, . and - characters. So we normalize
    # it and slice at 150 characters.
    if settings.OIDC_USERNAME_CLAIM in claims and claims[settings.OIDC_USERNAME_CLAIM]:
        username = claims[settings.OIDC_USERNAME_CLAIM]
    else:
        username = email
    return unicodedata.normalize("NFKC", username)[:150]


def normalize_url(url: str) -> str:
    if not url or not isinstance(url, str):
        return ""

    url = url.strip()
    if not url:
        return ""

    try:
        parsed = urllib.parse.urlparse(url)

        # Normalize the scheme to lowercase
        scheme = parsed.scheme.lower()

        # Normalize the netloc (domain) to lowercase
        netloc = parsed.hostname.lower() if parsed.hostname else ""
        if parsed.port:
            netloc += f":{parsed.port}"
        if parsed.username:
            auth = parsed.username
            if parsed.password:
                auth += f":{parsed.password}"
            netloc = f"{auth}@{netloc}"

        # Remove trailing slashes from all paths
        path = parsed.path.rstrip("/") if parsed.path else ""

        # Sort query parameters alphabetically
        query = ""
        if parsed.query:
            query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            query_params.sort(key=lambda x: (x[0], x[1]))
            query = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)

        # Keep fragment as-is
        fragment = parsed.fragment

        # Reconstruct the normalized URL
        return urllib.parse.urlunparse(
            (scheme, netloc, path, parsed.params, query, fragment)
        )

    except (ValueError, AttributeError):
        return url
