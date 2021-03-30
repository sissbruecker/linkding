from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.utils import timezone


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


def humanize_time_delta(from_date: datetime, to_date: datetime = timezone.now()):
    delta = relativedelta(to_date, from_date)

    if delta.years > 1:
        return f'{delta.years} years ago'
    elif delta.years == 1:
        return 'a year ago'
    elif delta.months > 1:
        return f'{delta.months} months ago'
    elif delta.months == 1:
        return 'a month ago'
    elif delta.weeks > 1:
        return f'{delta.weeks} weeks ago'
    elif delta.weeks == 1:
        return 'a week ago'
    else:
        yesterday = to_date - relativedelta(days=1)
        if from_date.day == to_date.day:
            return 'today'
        elif from_date.day == yesterday.day:
            return 'yesterday'
        else:
            return weekday_names[from_date.isoweekday()]
