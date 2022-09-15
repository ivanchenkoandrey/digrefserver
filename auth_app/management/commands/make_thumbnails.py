import os

from django.conf import settings
from django.core.management.base import BaseCommand

from utils.crop_photos import crop_image

USERS_PHOTO_PATH = f"{settings.BASE_DIR}/media/users_photo/"
TRANSACTION_PHOTO_PATH = f"{settings.BASE_DIR}/media/transactions/"


class Command(BaseCommand):
    def handle(self, *args, **options):
        for item in os.listdir(USERS_PHOTO_PATH):
            crop_image(item, USERS_PHOTO_PATH)
        for item in os.listdir(TRANSACTION_PHOTO_PATH):
            crop_image(item, TRANSACTION_PHOTO_PATH)
