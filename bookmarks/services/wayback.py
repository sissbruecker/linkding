import time
from typing import Dict

import waybackpy
import waybackpy.utils
from waybackpy.exceptions import NoCDXRecordFound


class CustomWaybackMachineCDXServerAPI(waybackpy.WaybackMachineCDXServerAPI):
    """
    Customized WaybackMachineCDXServerAPI to work around some issues with retrieving the newest snapshot.
    See https://github.com/akamhy/waybackpy/issues/176
    """

    def newest(self):
        unix_timestamp = int(time.time())
        self.closest = waybackpy.utils.unix_timestamp_to_wayback_timestamp(unix_timestamp)
        self.sort = 'closest'
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
        payload['fastLatest'] = 'true'
