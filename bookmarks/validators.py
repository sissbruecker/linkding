from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError


class BookmarkURLValidator(validators.URLValidator):
    """
    Extends default Django URLValidator and cancels validation if it is disabled in settings.
    This allows to switch URL validation on/off dynamically which helps with testing
    """

    def __call__(self, value):
        if settings.LD_DISABLE_URL_VALIDATION:
            return

        if value == "":
            raise ValidationError("URL can't be empty")
        super().__call__(value)
