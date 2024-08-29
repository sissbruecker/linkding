import datetime

from django.utils import timezone


def generate_fallback_webarchive_url(
    url: str, timestamp: datetime.datetime
) -> str | None:
    """
    Generate a URL to the web archive for the given URL and timestamp.
    A snapshot for the specific timestamp might not exist, in which case the
    web archive will show the closest snapshot to the given timestamp.
    If there is no snapshot at all the URL will be invalid.
    """
    if not url:
        return None
    if not timestamp:
        timestamp = timezone.now()

    return f"https://web.archive.org/web/{timestamp.strftime('%Y%m%d%H%M%S')}/{url}"
