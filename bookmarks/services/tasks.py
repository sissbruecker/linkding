import logging

import waybackpy
from background_task import background
from waybackpy.exceptions import WaybackError

from bookmarks.models import Bookmark

logger = logging.getLogger(__name__)


@background()
def create_web_archive_snapshot(bookmark_id: int):
    bookmark = None
    try:
        bookmark = Bookmark.objects.get(id=bookmark_id)
    except Bookmark.DoesNotExist:
        pass

    if not bookmark:
        return

    logger.debug(f'Saving archive for bookmark: {bookmark}...')

    wayback = waybackpy.Url(bookmark.url)

    try:
        archive = wayback.save()
    except WaybackError as error:
        logger.exception(f'Error saving for bookmark: {bookmark}...', exc_info=error)
        raise

    bookmark.archive_url = archive.archive_url
    bookmark.save()
    logger.debug(f'Successfully saved archive for bookmark: {bookmark}...')
