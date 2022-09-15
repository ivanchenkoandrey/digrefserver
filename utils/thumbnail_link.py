from django.conf import settings

SUFFIX = settings.THUMBNAIL_SUFFIX


def get_thumbnail_link(photo_link: str) -> str:
    thumbnail_link = photo_link.split('.')
    thumbnail_link[-1] = f"{SUFFIX}.{thumbnail_link[-1]}"
    return ''.join(thumbnail_link)
