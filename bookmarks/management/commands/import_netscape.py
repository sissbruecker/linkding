from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from bookmarks.services.importer import import_netscape_html


class Command(BaseCommand):
    help = "Import Netscape HTML bookmark file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to file")
        parser.add_argument(
            "user", type=str, help="Name of the user for which to import"
        )

    def handle(self, *args, **kwargs):
        filepath = kwargs["file"]
        username = kwargs["user"]
        with open(filepath) as html_file:
            html = html_file.read()
        user = User.objects.get(username=username)

        import_netscape_html(html, user)
