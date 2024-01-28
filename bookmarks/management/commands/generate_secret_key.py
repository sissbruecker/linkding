import logging
import os

from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate secret key file if it does not exist"

    def handle(self, *args, **options):
        secret_key_file = os.path.join("data", "secretkey.txt")

        if os.path.exists(secret_key_file):
            logger.info(f"Secret key file already exists")
            return

        secret_key = get_random_secret_key()
        with open(secret_key_file, "w") as f:
            f.write(secret_key)
        logger.info(f"Generated secret key file")
