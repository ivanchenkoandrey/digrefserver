import datetime
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from rest_framework import status, authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.accounts_data import processing_accounts_data
from utils.custom_permissions import IsSystemAdmin, IsOrganizationAdmin
from .models import Period, UserStat, Account, Transaction, Profile
from .serializers import (UserSerializer, SearchUserSerializer,
                          PeriodSerializer, ProfileSerializer)
from .service import (get_search_user_data)

User = get_user_model()

logger = logging.getLogger(__name__)


class ProfileView(APIView):
    """
    Выводит информацию о пользователе
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        profile_serializer = UserSerializer(user)
        logger.info(f"Пользователь {request.user} зашёл на страницу профиля")
        return Response(profile_serializer.data)


class GetProfileView(RetrieveAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer


class UserBalanceView(APIView):
    """
    Выводит информацию о балансе пользователя
    """
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
    """
    Выводит информацию для пользователя в зависимости от периода
    """
    data = processing_accounts_data(request.user, period_id)
    logger.info(f"Пользователь {request.user} зашёл на "
                f"страницу отдельного периода с id {period_id}")
    return Response(data)


class SearchUserView(APIView):
    """
    Поиск пользователя по вхождению искомой строки
    (никнейм в Telegram, имя, фамилия или электронная почта)
    """
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


class PeriodListView(ListAPIView):
    """
    Возвращает список периодов, в которые осуществлялась раздача спасибок
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    serializer_class = PeriodSerializer
    queryset = Period.objects.all()


class UsersList(APIView):
    """
    Возвращает список пользователей по умолчанию
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        if request.data.get('get_users') is not None:
            logger.info(f'Запрос на показ пользователей по умолчанию от {request.user}')
            users_list = User.objects.exclude(username__in=[request.user.username]).order_by('profile__surname').annotate(
                user_id=F('id'),
                tg_name=F('profile__tg_name'),
                name=F('profile__first_name'),
                surname=F('profile__surname'),
                photo=F('profile__photo')).values('user_id', 'tg_name', 'name', 'surname', 'photo')[:10]
            return Response(users_list)
        logger.info(f'Неправильный запрос на показ пользователей по умолчанию от {request.user}: {request.data}')
        return Response(status=status.HTTP_400_BAD_REQUEST)


class BurnThanksView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin]

    @classmethod
    def get(cls, request, *args, **kwargs):
        today = datetime.date.today()
        burnt_account = Account.objects.get(account_type='B')
        system = User.objects.get(username='system')
        previous_period = Period.objects.filter(end_date__lt=today).order_by('-end_date').first()
        logger.info(f"{previous_period=}")
        stats = UserStat.objects.select_related('user').filter(period=previous_period)
        accounts = Account.objects.select_related('owner').filter(account_type='D', owner__stats__in=stats)
        data = {}
        with transaction.atomic():
            for stat in stats:
                if stat.distr_burnt == 0:
                    account = accounts.get(owner_id=stat.user.pk)
                    stat.distr_burnt = account.amount
            UserStat.objects.bulk_update(stats, ['distr_burnt'])
            overall_burnt = 0
            for account in accounts:
                if account.amount > 0:
                    overall_burnt += account.amount
                    Transaction.objects.create(
                        sender=account.owner,
                        recipient=system,
                        amount=account.amount,
                        reason=f"burnt from {account.owner}",
                        status='R',
                        is_anonymous=True,
                        is_public=False
                    )
                    account.amount = 0
            Account.objects.bulk_update(accounts, ['amount'])
            if overall_burnt:
                burnt_account.amount += overall_burnt
                burnt_account.save(update_fields=['amount'])
        return Response(data)
