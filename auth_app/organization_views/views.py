from secrets import randbelow

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from rest_framework import authentication, status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
import logging

from auth_app.models import Organization, Profile
from utils.crypts import encrypt_message, decrypt_message
from utils.custom_permissions import IsSystemAdmin, IsDepartmentAdmin, IsOrganizationAdmin
from .serializers import (RootOrganizationSerializer,
                          DepartmentSerializer,
                          FullOrganizationSerializer,
                          OrganizationImageSerializer)

User = get_user_model()
BOT_TOKEN = settings.BOT_TOKEN
bot = TeleBot(token=BOT_TOKEN)
logger = logging.getLogger(__name__)


class CreateRootOrganization(CreateAPIView):
    """
    Создание организации верхнего уровня
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin]
    queryset = Organization.objects.all()
    serializer_class = RootOrganizationSerializer


class OrganizationDetailView(RetrieveAPIView):
    """
    Детальная страница организации
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    queryset = Organization.objects.all()
    serializer_class = FullOrganizationSerializer


class CreateDepartmentView(APIView):
    """
    Создание подразделения
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsOrganizationAdmin | IsDepartmentAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        data = request.data.copy()
        if data.get('parent_id') is None or data.get('top_id') is None:
            return Response('У подразделения должны быть parent_id '
                            '(вышестоящее подразделение) и top_id (юридическое лицо)',
                            status=status.HTTP_400_BAD_REQUEST)
        data.update({"organization_type": "D"})
        serializer = DepartmentSerializer(data=data, context={"request": request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class RootOrganizationListView(ListAPIView):
    """
    Cписок организаций верхнего уровня
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin | IsOrganizationAdmin | IsDepartmentAdmin]
    queryset = Organization.objects.filter(parent_id=None)
    serializer_class = FullOrganizationSerializer


class DepartmentsListView(APIView):
    """
    Список всех подразделений переданной организации
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin | IsOrganizationAdmin | IsDepartmentAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        organization_id = request.data.get('organization_id')
        if organization_id is not None:
            try:
                root_organization = Organization.objects.get(pk=organization_id)
                departments = root_organization.children.all()

                serializer = FullOrganizationSerializer(departments, many=True)
                return Response(serializer.data)
            except Organization.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной организации",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр organization_id",
                        status=status.HTTP_400_BAD_REQUEST)


class UpdateOrganizationLogoView(UpdateAPIView):
    """
    Обновление логотипа организации
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin | IsOrganizationAdmin | IsDepartmentAdmin]
    queryset = Organization.objects.all()
    serializer_class = OrganizationImageSerializer


class SendCodeToChangeOrganizationView(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def post(cls, request, *args, **kwargs):
        current_user = User.objects.select_related('profile').filter(pk=request.user.pk).first()
        tg_id = current_user.profile.tg_id
        organization_id = request.data.get('organization_id')
        if organization_id == current_user.profile.organization_id:
            raise ValidationError('Вы уже залогинены в данную организацию')
        if organization_id is None:
            raise ValidationError('Передайте параметр organization_id')
        if not Profile.objects.filter(tg_id=tg_id, organization_id=organization_id).exists():
            raise ValidationError('Не найден пользователь с таким айди телеграм и айди организации')
        else:
            code = ''.join([str(randbelow(10)) for _ in range(4)])
            response = Response()
            try:
                bot.send_message(tg_id, f'{code} - код подтверждения для смены текущей организации')
            except ApiTelegramException:
                raise ValidationError('Неизвестный боту пользователь')
            response.data = {'status': 'Код для подтверждения смены организации отправлен в телеграм'}
            response['X-Code'] = request.session['x-code'] = encrypt_message(code)
            response['organization_id'] = request.session['organization_id'] = encrypt_message(str(organization_id))
            response['tg_id'] = request.session['tg_id'] = encrypt_message(tg_id)
            return response


class ChangeOrganizationView(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def post(cls, request, *args, **kwargs):
        code = request.data.get('code')
        if code is None:
            raise ValidationError('Передайте параметр code')
        current_user = request.user
        current_user_tg_id = current_user.profile.tg_id
        encrypted_code = request.headers.get('X-Code', '') or request.session.get('x-code', '')
        encrypted_organization_id = (request.headers.get('organization_id', '')
                                     or request.session.get('organization_id', ''))
        encrypted_tg_id = (request.headers.get('tg_id', '')
                           or request.session.get('tg_id', ''))
        tg_id = decrypt_message(encrypted_tg_id)
        if tg_id != current_user_tg_id:
            return Response(data={"status": False, "reason": "Invalid tg_id in headers"},
                            status=status.HTTP_401_UNAUTHORIZED)
        decrypted_code = decrypt_message(encrypted_code)
        if code != decrypted_code:
            return Response(data={"status": False, "reason": "Invalid code"}, status=status.HTTP_401_UNAUTHORIZED)
        organization_id = decrypt_message(encrypted_organization_id)
        other_user = User.objects.filter(profile__tg_id=tg_id, profile__organization_id=organization_id).first()
        if other_user is not None:
            token = Token.objects.get(user=other_user).key
            logout(request)
            login(request, other_user)
            data = {'type': 'authresult',
                    "is_success": True,
                    "token": token,
                    "sessionid": request.session.session_key}
            return Response(data=data)
        return Response(data={"status": False, "reason": "User not found"}, status=status.HTTP_404_NOT_FOUND)


class GetUserOrganizations(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        current_user = User.objects.select_related('profile').filter(pk=request.user.pk).first()
        tg_id = current_user.profile.tg_id
        related_organization_ids = set(User.objects.filter(profile__tg_id=tg_id)
                                       .exclude(pk=current_user.pk)
                                       .values_list('profile__organization_id', flat=True))
        organizations_data = Organization.objects.filter(pk__in=related_organization_ids).values(
            'name', 'id'
        )
        return Response(data=organizations_data)
