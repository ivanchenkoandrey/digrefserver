import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse
from rest_framework import authentication, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from utils.accounts_data import processing_accounts_data

from .service import create_admin_report, export_user_transactions

TELEGRAM_BOT_AUTH_TOKEN = settings.TELEGRAM_BOT_AUTH_TOKEN

logger = logging.getLogger(__name__)


User = get_user_model()


class TgBotOnly(BasePermission):
    def has_permission(self, request, view):
        token_object = Token.objects.filter(key=TELEGRAM_BOT_AUTH_TOKEN).first()
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


class GetAnalyticsAdmin(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [TgBotOnly]

    @classmethod
    def post(cls, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if telegram_id:
            admins_list = list(User.objects
                               .filter(privileged__role='A')
                               .values_list('profile__tg_id', flat=True))
            if telegram_id in admins_list:
                filename = create_admin_report()
                return FileResponse(open(filename, 'rb'))
            return Response({"status": "Вы не являетесь администратором"},
                            status=status.HTTP_403_FORBIDDEN)
        return Response('Необходимо передать telegram_id пользователя',
                        status=status.HTTP_400_BAD_REQUEST)


class ExportUserTransactions(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [TgBotOnly]

    @classmethod
    def post(cls, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if telegram_id:
            is_user_exists = User.objects.filter(profile__tg_id=telegram_id).exists()
            if is_user_exists:
                filename = export_user_transactions(telegram_id)
                return FileResponse(open(filename, 'rb'))
            return Response({"status": f"Пользователь с {telegram_id=} не найден"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response('Необходимо передать telegram_id пользователя',
                        status=status.HTTP_400_BAD_REQUEST)


class ExportUserBalance(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [TgBotOnly]

    @classmethod
    def post(cls, request, *args, **kwargs):
        telegram_id = request.data.get('telegram_id')
        if telegram_id:
            user = User.objects.filter(profile__tg_id=telegram_id).first()
            if user is not None:
                data = processing_accounts_data(user)
                return Response(data)
            return Response({"status": f"Пользователь с {telegram_id=} не найден"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response('Необходимо передать telegram_id пользователя',
                        status=status.HTTP_400_BAD_REQUEST)
