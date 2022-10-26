from rest_framework.exceptions import ValidationError


def validate_token_request(old_token, new_token):
    if old_token is None:
        raise ValidationError("Передайте параметр old_token")
    if new_token is None:
        raise ValidationError("Передайте параметр new_token")
    return True
