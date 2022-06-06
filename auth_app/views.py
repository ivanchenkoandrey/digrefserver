from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from rest_framework import serializers, status, authentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from .models import Profile

User = get_user_model()

BOT_TOKEN = "5366571103:AAFxD1Yv5wM3TOPv7W5LfgJevOlfXqkp5AQ"

bot = TeleBot(token=BOT_TOKEN)


class TelegramIDSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    tg_id = serializers.CharField(max_length=20)


class VerifyCodeSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=8)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['tg_id']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ['username', 'profile']


class AuthView(APIView):
    @classmethod
    def post(cls, request, *args, **kwargs):
        code = '1234'
        request.session['code'] = code
        serializer = TelegramIDSerializer(data=request.data)
        if serializer.is_valid():
            tg_id = serializer.data.get('tg_id')
            try:
                bot.send_message(tg_id, f'Your register code is {code}')
            except ApiTelegramException:
                return Response(data={"error": "Chat id is invalid"}, status=status.HTTP_400_BAD_REQUEST)
            request.session['tg_id'] = tg_id
            return redirect('verify')
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
        tg_id = request.session['tg_id']
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.data.get('code')
            if code == request.session.get('code'):
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
