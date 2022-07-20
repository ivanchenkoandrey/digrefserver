import logging
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, authentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from utils.accounts_data import processing_accounts_data
from utils.crypts import encrypt_message, decrypt_message
from utils.custom_permissions import IsController
from .models import Profile, Transaction
from .serializers import (TelegramIDSerializer, VerifyCodeSerializer,
                          UserSerializer, TransactionPartialSerializer,
                          TransactionFullSerializer, SearchUserSerializer,
                          TransactionCancelSerializer)
from .service import (update_transactions_by_controller,
                      get_search_user_data, is_controller_data_is_valid,
                      cancel_transaction_by_user)

User = get_user_model()

logger = logging.getLogger(__name__)

BOT_TOKEN = settings.BOT_TOKEN
SECRET_KEY = settings.SECRET_KEY

bot = TeleBot(token=BOT_TOKEN)


class AuthView(APIView):
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
                return Response(data={"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
            tg_id = user_profile.tg_id
            try:
                bot.send_message(tg_id, f'Your register code is {code}')
            except ApiTelegramException:
                logger.error(f"Передан неизвестный боту telegram_id: {tg_id}, "
                             f"IP: {request.META.get('REMOTE_ADDR')}")
                return Response(data={"error": "Chat id is invalid"}, status=status.HTTP_400_BAD_REQUEST)
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


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        profile_serializer = UserSerializer(user)
        logger.info(f"Пользователь {request.user} зашёл на страницу профиля")
        return Response(profile_serializer.data)


class UserBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        data = processing_accounts_data(request.user)
        logger.info(f"Пользователь {request.user} зашёл на страницу баланса")
        return Response(data)


@api_view(http_method_names=['GET'])
@authentication_classes([authentication.SessionAuthentication,
                         authentication.TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_stat_by_period(request, period_id):
    data = processing_accounts_data(request.user, period_id)
    logger.info(f"Пользователь {request.user} зашёл на "
                f"страницу отдельного периода с id {period_id}")
    return Response(data)


class SendCoinView(CreateModelMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    queryset = Transaction.objects.all()
    serializer_class = TransactionPartialSerializer

    def post(self, request, *args, **kwargs):
        logger.info(f"Пользователь {request.user} отправил "
                    f"следующие данные для совершения транзакции: {request.data}")
        return self.create(request, *args, **kwargs)


class CancelTransactionByUserView(UpdateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionCancelSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    def update(self, request, *args, **kwargs):
        logger.info(f"Пользователь {request.user} отправил "
                    f"следующие данные для отмены транзакции: {request.data}")
        instance: Transaction = self.get_object()
        if instance.status == 'D':
            logger.info(f"Попытка отмены транзакции с id {instance.pk} пользователем {request.user}")
            return Response(f"Транзакция уже отменена", status=status.HTTP_400_BAD_REQUEST)
        timedelta = timezone.now() - instance.created_at
        if timedelta.seconds > settings.GRACE_PERIOD:
            logger.info(f"Попытка отменить транзакцию с id {instance.pk} пользователем {request.user} "
                        f"по истечении grace периода (превышение {timedelta.seconds - settings.GRACE_PERIOD} секунд)")
            return Response(f"Время возможности отмены транзакции истекло", status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            cancel_transaction_by_user(instance, request, serializer)
            return Response(serializer.data)


class VerifyOrCancelTransactionByControllerView(APIView):
    permission_classes = [IsController]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        queryset = Transaction.objects.filter_to_use_by_controller().order_by('-created_at')
        serializer = TransactionFullSerializer(queryset, many=True)
        logger.info(f"Контроллер {request.user} смотрит список транзакций для подтверждения / отклонения")
        return Response(serializer.data)

    @classmethod
    def put(cls, request, *args, **kwargs):
        data = request.data
        if is_controller_data_is_valid(data):
            response = update_transactions_by_controller(data, request)
            logger.info(f"Контроллер {request.user} выполнил подтверждение / отклонение транзакций")
            return Response(response)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class TransactionsByUserView(ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    serializer_class = TransactionFullSerializer

    def get(self, request, *args, **kwargs):
        logger.info(f"Пользователь {self.request.user} смотрит список транзакций")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Transaction.objects.filter_by_user(self.request.user).order_by('-updated_at')


class SingleTransactionByUserView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    serializer_class = TransactionFullSerializer

    def get(self, request, *args, **kwargs):
        _transaction = self.get_object()
        logger.info(f"Пользователь {self.request.user} смотрит "
                    f"транзакцию c id {_transaction.pk}")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Transaction.objects.filter_by_user(self.request.user)


class SearchUserView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        serializer = SearchUserSerializer(data=request.data)
        if serializer.is_valid():
            users_data = cls.get_search_data(request, serializer)
            return Response(users_data)
        logger.info(f"Неверный запрос на поиск пользователей: {request.data}")
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @classmethod
    def get_search_data(cls, request, serializer):
        data = serializer.data.get('data')
        logger.info(f"Пользователь {request.user} ищет пользователя, используя "
                    f"следующие данные: {data}")
        users_data = get_search_user_data(data, request)
        return users_data
