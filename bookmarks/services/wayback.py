import datetime
import time
from typing import Dict

import waybackpy
import waybackpy.utils
from django.utils import timezone
from waybackpy.exceptions import NoCDXRecordFound


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


class CustomWaybackMachineCDXServerAPI(waybackpy.WaybackMachineCDXServerAPI):
    """
    Customized WaybackMachineCDXServerAPI to work around some issues with retrieving the newest snapshot.
    See https://github.com/akamhy/waybackpy/issues/176
    """

    def newest(self):
        unix_timestamp = int(time.time())
        self.closest = waybackpy.utils.unix_timestamp_to_wayback_timestamp(
            unix_timestamp
        )
        self.sort = "closest"
        self.limit = -5

        newest_snapshot = None
        for snapshot in self.snapshots():
            newest_snapshot = snapshot
            break

        if not newest_snapshot:
            raise NoCDXRecordFound(
                "Wayback Machine's CDX server did not return any records "
                + "for the query. The URL may not have any archives "
                + " on the Wayback Machine or the URL may have been recently "
                + "archived and is still not available on the CDX server."
            )

        return newest_snapshot

    def add_payload(self, payload: Dict[str, str]) -> None:
        super().add_payload(payload)
        # Set fastLatest query param, as we are only using this API to get the latest snapshot and using fastLatest
        # makes searching for latest snapshots faster
        payload["fastLatest"] = "true"
