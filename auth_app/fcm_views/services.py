from rest_framework.exceptions import ValidationError

from auth_app.models import FCMToken


def validate_token_request(device, token):
    if device is None:
        raise ValidationError("Передайте параметр device")
    if token is None:
        raise ValidationError("Передайте параметр token")
    return True


def update_or_create_fcm_token(device, token, user):
    fcm_token_entry = FCMToken.objects.filter(device=device, user=user).first()
    if fcm_token_entry is not None:
        fcm_token_entry.token = token
        fcm_token_entry.save(update_fields=['token'])
        created = False
    else:
        fcm_token_entry = FCMToken.objects.create(device=device, token=token, user=user)
        created = True
    return fcm_token_entry, created
