from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import authentication, status
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Account, Organization, Transaction, UserStat
from utils.current_period import get_current_period
from utils.custom_permissions import IsSystemAdmin

User = get_user_model()


class EmitDistributionThanks(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin]

    @classmethod
    def get(cls, request, *args, **kwargs):
        period = get_current_period(request.user.profile.organization_id)
        if period:
            emit_user = User.objects.get(username='system')
            organization = Organization.objects.get(pk=1)
            emit_account = Account.objects.get(account_type='T', challenge_id=None)
            accounts = Account.objects.filter(account_type='D', amount=0, challenge_id=None)
            users_pk = list(accounts.values_list('owner_id', flat=True))
            users = User.objects.filter(pk__in=users_pk)
            user_stats = UserStat.objects.filter(period=period, user_id__in=users_pk)
            with transaction.atomic():
                emit_counter = 0
                for account in accounts:
                    user = users.get(pk=account.owner_id)
                    emit_transaction = Transaction.objects.create(
                        sender=emit_user,
                        recipient=user,
                        amount=150,
                        reason='Эмиссия на начало периода',
                        status='R',
                        transaction_class='E',
                        is_public=False,
                        is_anonymous=False,
                        period=period,
                        organization=organization,
                        scope=organization
                    )
                    account.amount += emit_transaction.amount
                    account.save(update_fields=['amount'])
                    emit_counter += emit_transaction.amount
                    stat = user_stats.get(user_id=user.pk)
                    stat.distr_initial = emit_transaction.amount
                    stat.save(update_fields=['distr_initial'])
                emit_account.amount -= emit_counter
                emit_account.save(update_fields=['amount'])
                if emit_counter:
                    return Response(status=status.HTTP_201_CREATED)
                return Response(status=status.HTTP_200_OK)
        else:
            return Response("Нет периода", status=status.HTTP_400_BAD_REQUEST)
