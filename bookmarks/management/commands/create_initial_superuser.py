import os
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creates an initial superuser for a deployment using env variables"

    def handle(self, *args, **options):
        User = get_user_model()
        superuser_name = os.getenv("LD_SUPERUSER_NAME", None)
        superuser_password = os.getenv("LD_SUPERUSER_PASSWORD", None)

        # Skip if option is undefined
        if not superuser_name:
            logger.info(
                "Skip creating initial superuser, LD_SUPERUSER_NAME option is not defined"
            )
            return

        # Skip if user already exists
        user_exists = User.objects.filter(username=superuser_name).exists()
        if user_exists:
            logger.info("Skip creating initial superuser, user already exists")
            return

        user = User(username=superuser_name, is_superuser=True, is_staff=True)

        if superuser_password:
            user.set_password(superuser_password)
        else:
            user.set_unusable_password()

        user.save()
        logger.info("Created initial superuser")
