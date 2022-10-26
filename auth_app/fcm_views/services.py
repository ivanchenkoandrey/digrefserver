from rest_framework.exceptions import ValidationError

from auth_app.models import FCMToken


def validate_token_request(device, token):
    if device is None:
        raise ValidationError("Передайте параметр device")
    if token is None:
        raise ValidationError("Передайте параметр token")
    return True


def update_or_create_fcm_token(device, token, user):
    return FCMToken.objects.update_or_create(device=device, token=token, user=user)
