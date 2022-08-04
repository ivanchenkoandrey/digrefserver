import logging
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db.models import Q
from rest_framework import status, authentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from auth_app.models import Profile
from auth_app.serializers import (TelegramIDSerializer, VerifyCodeSerializer)
from utils.crypts import encrypt_message, decrypt_message
from utils.custom_permissions import IsAnonymous


User = get_user_model()
logger = logging.getLogger(__name__)
BOT_TOKEN = settings.BOT_TOKEN
bot = TeleBot(token=BOT_TOKEN)


class AuthView(APIView):

    permission_classes = [IsAnonymous]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        code = ''.join([str(randint(1, 9)) for _ in range(4)])
        serializer = TelegramIDSerializer(data=request.data)
        if serializer.is_valid():
            _login = serializer.data.get('login')
            user_profile = Profile.objects.filter(Q(tg_name=_login) | Q(tg_id=_login)).first()
            if user_profile is None:
                logger.info(f"Не найден пользователь с telegram_id или username {_login}, "
                            f"IP: {request.META.get('REMOTE_ADDR')}")
                return Response(data={"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            tg_id = user_profile.tg_id
            try:
                bot.send_message(tg_id, f'Код подтверждения в системе Цифровое Спасибо: {code}')
            except ApiTelegramException:
                logger.error(f"Передан неизвестный боту telegram_id: {tg_id}, "
                             f"IP: {request.META.get('REMOTE_ADDR')}")
                return Response(data={"error": "Похоже, бот вас не знает"}, status=status.HTTP_400_BAD_REQUEST)
            logger.info(f"Пользователю {user_profile.tg_name} отправлен код {code}, "
                        f"IP: {request.META.get('REMOTE_ADDR')}")
            response = Response({'type': "authorize", "status": "ready to verify"})
            response['X-ID'] = request.session['x-id'] = encrypt_message(tg_id)
            response['X-Code'] = request.session['x-code'] = encrypt_message(code)
            return response
        logger.info(f"Ошибочный запрос аутентификации "
                    f"с IP адреса {request.META.get('REMOTE_ADDR')}, "
                    f"запрос: {request.data}")
        return Response(status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):

    permission_classes = [IsAnonymous]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        encrypted_id = request.headers.get('X-ID', '') or request.session.get('x-id', '')
        encrypted_code = request.headers.get('X-Code', '') or request.session.get('x-code', '')
        tg_id = decrypt_message(encrypted_id)
        decrypted_code = decrypt_message(encrypted_code)
        logger.info(f"Для пользователя с telegram_id {tg_id} к"
                    f"од подтверждения: {decrypted_code}, "
                    f"IP: {request.META.get('REMOTE_ADDR')}")
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.data.get('code')
            if code == decrypted_code:
                user = User.objects.get(profile__tg_id=tg_id)
                token = Token.objects.get(user=user).key
                login(request, user)
                data = {'type': 'authresult',
                        "is_success": True,
                        "token": token,
                        "sessionid": request.session.session_key}
                logger.info(f"Пользователь c telegram_id {tg_id} успешно аутентифицирован.")
                return Response(data)
            logger.info(f"Введён неправильный код подтверждения: {code}, "
                        f"IP: {request.META.get('REMOTE_ADDR')}")
        return Response(
            data={'type': 'authresult', "is_success": False},
            status=status.HTTP_400_BAD_REQUEST)
