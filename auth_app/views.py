from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers, status, authentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from utils.accounts_data import processing_accounts_data
from utils.crypts import encrypt_message, decrypt_message
from .models import Profile, Account

User = get_user_model()

BOT_TOKEN = settings.BOT_TOKEN
SECRET_KEY = settings.SECRET_KEY

bot = TeleBot(token=BOT_TOKEN)


class TelegramIDSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    tg_id = serializers.CharField(max_length=20)


class VerifyCodeSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=8)


class ProfileSerializer(serializers.ModelSerializer):
    organization = serializers.CharField(source="organization.name")
    department = serializers.CharField(source="department.name")

    class Meta:
        model = Profile
        exclude = ['user']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ['username', 'profile']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class AuthView(APIView):
    @classmethod
    def post(cls, request, *args, **kwargs):
        code = ''.join([str(randint(1, 9)) for _ in range(4)])
        serializer = TelegramIDSerializer(data=request.data)
        if serializer.is_valid():
            tg_id = serializer.data.get('tg_id')
            try:
                bot.send_message(tg_id, f'Your register code is {code}')
            except ApiTelegramException:
                return Response(data={"error": "Chat id is invalid"}, status=status.HTTP_400_BAD_REQUEST)
            response = Response({'type': "authorize", "status": "ready to verify"})
            response['X-ID'] = encrypt_message(tg_id)
            response['X-Code'] = encrypt_message(code)
            return response
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @classmethod
    def get(cls, request, *args, **kwargs):
        data = {'type': 'authorize', 'tg_id': None}
        serializer = TelegramIDSerializer(data)
        return Response(serializer.data)


class VerifyCodeView(APIView):

    @classmethod
    def get(cls, request, *args, **kwargs):
        data = {'type': 'authcode', 'code': None}
        serializer = VerifyCodeSerializer(data)
        return Response(serializer.data)

    @classmethod
    def post(cls, request, *args, **kwargs):
        tg_id = decrypt_message(request.headers.get('X-ID'))
        code_from_headers = decrypt_message(request.headers.get('X-Code'))
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.data.get('code')
            if code == code_from_headers:
                user = User.objects.get(profile__tg_id=tg_id)
                token = Token.objects.get(user=user).key
                data = {'type': 'authresult', "is_success": True, "token": token}
                return Response(data)
        return Response(
            data={'type': 'authresult', "is_success": False},
            status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        profile_serializer = UserSerializer(user)
        return Response(profile_serializer.data)


class UserBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        user = request.user
        queryset = Account.objects.filter(account_type__in=['I', 'D'], owner=user)
        data = processing_accounts_data(queryset)
        return Response(data)


@api_view(http_method_names=['GET'])
@authentication_classes([authentication.TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_stat_by_period(request, period_id):
    user = request.user
    queryset = Account.objects.filter(account_type__in=['I', 'D'], owner=user)
    data = processing_accounts_data(queryset)
    data["income"]["used_for_bonus"] = 200
    data["income"]["received"] += 200
    data["distr"]["burnt"] = 0
    data["bonus"] = 0
    return Response(data)
