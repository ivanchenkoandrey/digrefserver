import os

from django.conf import settings

from utils.crop_photos import crop_image
import uuid


def process_profile_image(profile):
    filename = profile.photo.name
    profile.photo.name = change_profile_filename(f"/media/{filename}").replace('media/', '')
    profile.save()
    crop_image(f"{profile.photo.name}", f"{settings.BASE_DIR}/media")


def change_profile_filename(filename: str) -> str:
    path = '/'.join(filename.split('/')[:-1])
    old_filename = filename.split('/')[-1]
    old_filename, extension = old_filename.rsplit('.', 1)
    new_filename = f"{path}/{uuid.uuid4().hex}.{extension}"
    os.rename(f"{settings.BASE_DIR}{filename}",
              f"{settings.BASE_DIR}/{new_filename}")
    return new_filename


def change_transaction_filename(filename: str) -> str:
    path = '/'.join(filename.split('/')[:-1])
    old_filename = filename.split('/')[-1]
    old_filename, extension = old_filename.rsplit('.', 1)
    new_filename = f"{path}/{uuid.uuid4().hex}.{extension}"
    os.rename(f"{settings.BASE_DIR}/media/{filename}",
              f"{settings.BASE_DIR}/media/{new_filename}")
    return new_filename
