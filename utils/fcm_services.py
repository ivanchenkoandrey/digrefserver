from auth_app.models import FCMToken


def get_fcm_tokens_list(user_id):
    return list(FCMToken.objects.filter(user_id=user_id)
                .values_list('token', flat=True))


def get_multiple_users_tokens_list(users_id_list):
    return list(FCMToken.objects.filter(user_id__in=users_id_list)
                .values_list('token', flat=True))
