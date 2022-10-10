from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import authentication, status
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import UserStat
from utils.current_period import get_current_period
from utils.custom_permissions import IsSystemAdmin

User = get_user_model()


class CreateUserStats(APIView):
    permission_classes = [IsSystemAdmin]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        period = get_current_period()
        user_stats = UserStat.objects.filter(period=period).exists()
        if not user_stats:
            users = User.objects.filter(~Q(username__in=['system', 'admin', 'digrefbot']))
            with transaction.atomic():
                stats = [UserStat(user=user, period=period) for user in users]
                data = UserStat.objects.bulk_create(stats)
                data = {str(stat.user): stat.to_json() for stat in data}
                return Response(data, status=status.HTTP_201_CREATED)
        return Response('Cтаты на период уже есть',
                        status=status.HTTP_200_OK)
