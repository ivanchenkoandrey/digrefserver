import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

TELEGRAM_BOT_AUTH_TOKEN = settings.TELEGRAM_BOT_AUTH_TOKEN

logger = logging.getLogger(__name__)


User = get_user_model()


class TgBotOnly(BasePermission):
    def has_permission(self, request, view):
        token_object = Token.objects.filter(key=TELEGRAM_BOT_AUTH_TOKEN).first()
        logger.info(f"{token_object=}, {request.user.pk=}")
        if token_object:
            return (request.user.is_authenticated
                    and request.user.pk == token_object.user_id)
        return False


class GetUserToken(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [TgBotOnly]

    @classmethod
    def post(cls, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if telegram_id:
            token = Token.objects.filter(user__profile__tg_id=telegram_id).first()
            if token:
                return Response({'token': token.key})
            return Response({'status': 'Пользователь с таким telegram_id не найден'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response('Необходимо передать telegram_id пользователя',
                        status=status.HTTP_400_BAD_REQUEST)
