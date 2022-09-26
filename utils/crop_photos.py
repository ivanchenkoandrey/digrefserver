import os

from PIL import Image, ExifTags
from django.conf import settings

_SIZE = (256, 256)
SUFFIX = settings.THUMBNAIL_SUFFIX


def crop_image(item, path, to_square=True):
    image = Image.open(f"{path}{item}")
    filename, extension = os.path.splitext(item)
    if extension in ('.jpg', '.JPG', '.jpeg', '.JPEG'):
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = dict(image._getexif().items())
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
        except (AttributeError, KeyError):
            pass
    if filename.endswith(SUFFIX):
        return
    image.thumbnail(_SIZE)
    image.save(f"{path}{filename}{SUFFIX}{extension}")
    if to_square:
        thumb_image = Image.open(f"{path}{filename}{SUFFIX}{extension}")
        need_width = need_height = 128
        cropped = crop_center(thumb_image, need_width, need_height)
        cropped.save(f"{path}{filename}{SUFFIX}{extension}")


def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    if img_width < crop_width:
        crop_width = 96
    if img_height < crop_height:
        crop_height = 96
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))
