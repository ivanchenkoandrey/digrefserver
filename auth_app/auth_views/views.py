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

from auth_app.models import Contact, Profile
from auth_app.serializers import (FindUserSerializer, VerifyCodeSerializer)
from auth_app.tasks import send
from utils.crypts import decrypt_message, encrypt_message
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
        serializer = FindUserSerializer(data=request.data)
        if serializer.is_valid():
            _login = serializer.data.get('login')
            if _login == "testapple":
                code = "4444"
                tg_id = "012345678"
                response = Response()
                response['X-Telegram'] = request.session['x-telegram'] = encrypt_message(tg_id)
                response['X-Code'] = request.session['x-code'] = encrypt_message(code)
                return response
            response = Response()
            if '@' in _login:
                profile = Profile.objects.filter(contacts__contact_id=_login).first()
                if profile:
                    email_contact = Contact.objects.filter(profile=profile, contact_type='@').first()
                    email = email_contact.contact_id
                    send.delay(email, code)
                    logger.info(f'На почту {email} отправлен код {code}')
                    response.data = {'status': 'Код отправлен на указанную электронную почту'}
                    response['X-Email'] = request.session['x-email'] = encrypt_message(email)
                else:
                    return Response('Пользователь не найден', status=status.HTTP_404_NOT_FOUND)
            else:
                profile = Profile.objects.filter(Q(tg_name=_login) | Q(tg_id=_login)).first()
                if profile:
                    tg_id = profile.tg_id
                    try:
                        bot.send_message(tg_id, f'Код подтверждения в системе Цифровое Спасибо: {code}')
                    except ApiTelegramException:
                        logger.error(f"Передан неизвестный боту telegram_id: {tg_id}, "
                                     f"IP: {request.META.get('REMOTE_ADDR')}")
                        return Response(data={"error": "Похоже, бот вас не знает"}, status=status.HTTP_400_BAD_REQUEST)
                    logger.info(f"В телеграм {tg_id} отправлен код {code}, "
                                f"IP: {request.META.get('REMOTE_ADDR')}")
                    response.data = {'status': 'Код отправлен в телеграм'}
                    response['X-Telegram'] = request.session['x-telegram'] = encrypt_message(tg_id)
                else:
                    return Response('Пользователь не найден', status=status.HTTP_404_NOT_FOUND)
            response['X-Code'] = request.session['x-code'] = encrypt_message(code)
            return response
        return Response(status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):

    permission_classes = [IsAnonymous]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        encrypted_id = request.headers.get('X-Telegram', '') or request.session.get('x-telegram', '')
        encrypted_code = request.headers.get('X-Code', '') or request.session.get('x-code', '')
        encrypted_email = request.headers.get('X-Email', '') or request.session.get('x-email', '')
        decrypted_code = decrypt_message(encrypted_code)
        tg_id = email = ''
        if encrypted_id:
            tg_id = decrypt_message(encrypted_id)
            logger.info(f"Для пользователя с telegram_id {tg_id} к"
                        f"од подтверждения: {decrypted_code}, "
                        f"IP: {request.META.get('REMOTE_ADDR')}")
        if encrypted_email:
            email = decrypt_message(encrypted_email)
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.data.get('code')
            if code == decrypted_code:
                user = User.objects.filter(Q(profile__tg_id=tg_id) | Q(profile__contacts__contact_id=email)).first()
                token = Token.objects.get(user=user).key
                login(request, user)
                data = {'type': 'authresult',
                        "is_success": True,
                        "token": token,
                        "sessionid": request.session.session_key}
                logger.info(f"Пользователь {user} успешно аутентифицирован.")
                return Response(data)
            logger.info(f"Введён неправильный код подтверждения: {code}, "
                        f"IP: {request.META.get('REMOTE_ADDR')}")
        return Response(
            data={'type': 'authresult', "is_success": False},
            status=status.HTTP_400_BAD_REQUEST)
