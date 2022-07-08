from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.db.models import Q, F
from django.http import JsonResponse
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
from .models import Profile, Account, Transaction
from .serializers import (TelegramIDSerializer, VerifyCodeSerializer,
                          UserSerializer, TransactionPartialSerializer,
                          TransactionFullSerializer, SearchUserSerializer,
                          TransactionCancelSerializer)

User = get_user_model()

BOT_TOKEN = settings.BOT_TOKEN
SECRET_KEY = settings.SECRET_KEY

bot = TeleBot(token=BOT_TOKEN)


@api_view(http_method_names=['GET'])
def get_session_id(request):
    if not request.session.session_key:
        request.session.create()
    return JsonResponse({'sessionid': request.session.session_key})


class AuthView(APIView):
    @classmethod
    def post(cls, request, *args, **kwargs):
        code = ''.join([str(randint(1, 9)) for _ in range(4)])
        serializer = TelegramIDSerializer(data=request.data)
        if serializer.is_valid():
            _login = serializer.data.get('login')
            user_profile = Profile.objects.filter(Q(tg_name=_login) | Q(tg_id=_login)).first()
            if user_profile is None:
                return Response(data={"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
            tg_id = user_profile.tg_id
            try:
                bot.send_message(tg_id, f'Your register code is {code}')
            except ApiTelegramException:
                return Response(data={"error": "Chat id is invalid"}, status=status.HTTP_400_BAD_REQUEST)
            response = Response({'type': "authorize", "status": "ready to verify"})
            response['X-ID'] = request.session['x-id'] = encrypt_message(tg_id)
            response['X-Code'] = request.session['x-code'] = encrypt_message(code)
            return response
        return Response(status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):

    @classmethod
    def post(cls, request, *args, **kwargs):
        encrypted_id = request.headers.get('X-ID', '') or request.session.get('x-id', '')
        encrypted_code = request.headers.get('X-Code', '') or request.session.get('x-code', '')
        tg_id = decrypt_message(encrypted_id)
        decrypted_code = decrypt_message(encrypted_code)
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
                return Response(data)
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
        return Response(profile_serializer.data)


class UserBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        user = request.user
        queryset = Account.objects.filter(account_type__in=['I', 'D'], owner=user)
        data = processing_accounts_data(queryset)
        return Response(data)


@api_view(http_method_names=['GET'])
@authentication_classes([authentication.SessionAuthentication,
                         authentication.TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_stat_by_period(request, period_id):
    user = request.user
    queryset = Account.objects.filter(account_type__in=['I', 'D'], owner=user)
    data = processing_accounts_data(queryset)
    data["income"]["used_for_bonus"] = 200
    data["distr"]["burnt"] = 0
    data["bonus"] = 0
    return Response(data)


class SendCoinView(CreateModelMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    queryset = Transaction.objects.all()
    serializer_class = TransactionPartialSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class CancelTransactionView(UpdateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionCancelSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)


class TransactionsByUserView(ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    serializer_class = TransactionFullSerializer

    def get_queryset(self):
        return Transaction.objects.filter_by_user(self.request.user)


class SingleTransactionByUserView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    serializer_class = TransactionFullSerializer

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
            data = serializer.data.get('data')
            users_data = User.objects.filter(
                (Q(profile__tg_name__istartswith=data) |
                 Q(profile__first_name__istartswith=data) |
                 Q(profile__surname__istartswith=data) |
                 Q(profile__contacts__contact_id__istartswith=data)) &
                ~Q(profile__tg_name=request.user.profile.tg_name)
            ).annotate(
                user_id=F('id'),
                tg_name=F('profile__tg_name'),
                name=F('profile__first_name'),
                surname=F('profile__surname')).values('user_id', 'tg_name', 'name', 'surname')
            return Response(users_data)
        return Response(status=status.HTTP_400_BAD_REQUEST)
