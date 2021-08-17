import logging

import waybackpy
from background_task import background
from waybackpy.exceptions import WaybackError

from bookmarks.models import Bookmark

logger = logging.getLogger(__name__)


@background()
def create_web_archive_snapshot(bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        return

    logger.debug(f'Create web archive link for bookmark: {bookmark}...')

    wayback = waybackpy.Url(bookmark.url)

    try:
        archive = wayback.save()
    except WaybackError as error:
        logger.exception(f'Error creating web archive link for bookmark: {bookmark}...', exc_info=error)
        raise

    bookmark.web_archive_snapshot_url = archive.archive_url
    bookmark.save()
    logger.debug(f'Successfully created web archive link for bookmark: {bookmark}...')