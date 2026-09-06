import os
from collections.abc import Iterable

from django.conf.locale import LANG_INFO
from django.utils.translation import to_language

MESSAGE_FILES = ("django.po", "django.mo")


def discover_extra_languages(
    locale_dir: str, known_codes: Iterable[str]
) -> list[tuple[str, str]]:
    """
    Finds additional translations in a locale directory, e.g. the data folder.

    Returns (code, name) tuples in the format of the LANGUAGES setting for every
    sub directory that contains an LC_MESSAGES/django.po or django.mo file and
    whose language code is not in known_codes. The name is taken from Django's
    language info if available, otherwise the code is used.
    """
    if not os.path.isdir(locale_dir):
        return []

    known = {to_language(code) for code in known_codes}
    languages = []
    for entry in sorted(os.listdir(locale_dir)):
        messages_dir = os.path.join(locale_dir, entry, "LC_MESSAGES")
        if not os.path.isdir(messages_dir):
            continue
        if not any(
            os.path.isfile(os.path.join(messages_dir, name)) for name in MESSAGE_FILES
        ):
            continue
        code = to_language(entry)
        if code in known:
            continue
        name = LANG_INFO.get(code, {}).get("name_local", code)
        languages.append((code, name))

    return languages
