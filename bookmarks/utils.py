from datetime import datetime

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


def humanize_absolute_date(value: datetime, now=timezone.now()):
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


def humanize_relative_date(value: datetime, now: datetime = timezone.now()):
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
