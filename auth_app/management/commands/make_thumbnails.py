import logging
import os

from PIL import Image
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

SIZE = (128, 128)

PATH = f"{settings.BASE_DIR}/media/users_photo/"


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info(f"{PATH=}")
        for item in os.listdir(PATH):
            image = Image.open(f"{PATH}{item}")
            filename, extension = os.path.splitext(image)
            image.thumbnail(SIZE)
            image.save(f"{PATH}{filename}_thumbnail{extension}")
            logger.info(f"{item=}")
