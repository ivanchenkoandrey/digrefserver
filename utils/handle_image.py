import os
import uuid

from django.conf import settings

from utils.crop_photos import crop_image
from utils.thumbnail_link import get_thumbnail_link

import logging

logger = logging.getLogger(__name__)


def handle_uploaded_file(f, path, name):
    with open(f'{path}{name}', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def process_instance_image(instance, cropped_photo=None):
    filename = instance.photo.name
    instance.photo.name = change_profile_filename(f"/media/{filename}").replace('media/', '')
    new_filename = instance.photo.name
    instance.save()
    if cropped_photo is None:
        crop_image(f"{new_filename}", f"{settings.BASE_DIR}/media")
    else:
        handle_uploaded_file(cropped_photo, f"{settings.BASE_DIR}/", cropped_photo.name)
        crop_image(f"{cropped_photo.name}", f"{settings.BASE_DIR}/", to_square=False)
        temp_cropped_photo_address = get_thumbnail_link(f"{settings.BASE_DIR}/{cropped_photo.name}")
        new_cropped_photo_address = get_thumbnail_link(f"{settings.BASE_DIR}/media{new_filename}")
        os.replace(temp_cropped_photo_address, new_cropped_photo_address)
        os.remove(f"{settings.BASE_DIR}/{cropped_photo.name}")


def change_profile_filename(filename: str) -> str:
    path = '/'.join(filename.split('/')[:-1])
    old_filename = filename.split('/')[-1]
    old_filename, extension = old_filename.rsplit('.', 1)
    new_filename = f"{path}/{uuid.uuid4().hex}.{extension}"
    os.rename(f"{settings.BASE_DIR}{filename}",
              f"{settings.BASE_DIR}/{new_filename}")
    return new_filename


def change_filename(filename: str) -> str:
    path = '/'.join(filename.split('/')[:-1])
    old_filename = filename.split('/')[-1]
    old_filename, extension = old_filename.rsplit('.', 1)
    new_filename = f"{path}/{uuid.uuid4().hex}.{extension}"
    os.rename(f"{settings.BASE_DIR}/media/{filename}",
              f"{settings.BASE_DIR}/media/{new_filename}")
    return new_filename
