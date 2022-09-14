import logging
import os

from PIL import Image
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

_SIZE = (256, 256)
PATH = f"{settings.BASE_DIR}/media/users_photo/"
SUFFIX = '_thumbnail'


class Command(BaseCommand):
    def handle(self, *args, **options):
        for item in os.listdir(PATH):
            image = Image.open(f"{PATH}{item}")
            filename, extension = os.path.splitext(item)
            if not filename.endswith(SUFFIX):
                need_width, need_height = _SIZE
                cropped = crop_center(image, need_width, need_height)
                cropped.save(f"{PATH}{filename}{SUFFIX}{extension}")


def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))
