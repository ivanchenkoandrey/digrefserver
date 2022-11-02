from auth_app.models import FCMToken


def get_fcm_tokens_list(user_id):
    return list(FCMToken.objects.filter(user_id=user_id)
                .values_list('token', flat=True))
