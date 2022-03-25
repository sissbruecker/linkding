from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.template.defaultfilters import pluralize
from django.utils import timezone, formats


def unique(elements, key):
    return list({key(element): element for element in elements}.values())


weekday_names = {
    1: 'Monday',
    2: 'Tuesday',
    3: 'Wednesday',
    4: 'Thursday',
    5: 'Friday',
    6: 'Saturday',
    7: 'Sunday',
}


def humanize_absolute_date(value: datetime, now: Optional[datetime] = None):
    if not now:
        now = timezone.now()
    delta = relativedelta(now, value)
    yesterday = now - relativedelta(days=1)

    is_older_than_a_week = delta.years > 0 or delta.months > 0 or delta.weeks > 0

    if is_older_than_a_week:
        return formats.date_format(value, 'SHORT_DATE_FORMAT')
    elif value.day == now.day:
        return 'Today'
    elif value.day == yesterday.day:
        return 'Yesterday'
    else:
        return weekday_names[value.isoweekday()]


def humanize_relative_date(value: datetime, now: Optional[datetime] = None):
    if not now:
        now = timezone.now()
    delta = relativedelta(now, value)

    if delta.years > 0:
        return f'{delta.years} year{pluralize(delta.years)} ago'
    elif delta.months > 0:
        return f'{delta.months} month{pluralize(delta.months)} ago'
    elif delta.weeks > 0:
        return f'{delta.weeks} week{pluralize(delta.weeks)} ago'
    else:
        yesterday = now - relativedelta(days=1)
        if value.day == now.day:
            return 'Today'
        elif value.day == yesterday.day:
            return 'Yesterday'
        else:
            return weekday_names[value.isoweekday()]


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
        raise ValueError(f'{value} is not a valid timestamp')

    try:
        return datetime.utcfromtimestamp(timestamp).astimezone()
    except (OverflowError, ValueError, OSError):
        pass

    # Value exceeds the max. allowed timestamp
    # Try parsing as microseconds
    try:
        return datetime.utcfromtimestamp(timestamp / 1000).astimezone()
    except (OverflowError, ValueError, OSError):
        pass

    # Value exceeds the max. allowed timestamp
    # Try parsing as nanoseconds
    try:
        return datetime.utcfromtimestamp(timestamp / 1000000).astimezone()
    except (OverflowError, ValueError, OSError):
        pass

    # Timestamp is out of range
    raise ValueError(f'{value} exceeds maximum value for a timestamp')


def get_safe_return_url(return_url: str, fallback_url: str):
    # Use fallback if URL is none or URL is not on same domain
    if not return_url or not return_url.startswith('/'):
        return fallback_url
    return return_url
