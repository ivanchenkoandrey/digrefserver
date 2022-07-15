from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, F

from auth_app.models import Transaction, TransactionState, UserStat

User = get_user_model()


def update_transactions_by_controller(data, request):
    response = {}
    with transaction.atomic():
        for transaction_pk, transaction_status, reason in data:
            transaction_instance = Transaction.objects.get(pk=transaction_pk)
            TransactionState.objects.create(
                transaction=transaction_instance,
                controller=request.user,
                status=transaction_status,
                reason=reason
            )
            transaction_instance.status = transaction_status
            transaction_instance.save()
            sender_accounts = transaction_instance.sender.accounts.all()
            recipient_accounts = transaction_instance.recipient.accounts.all()
            sender_user_stat = UserStat.objects.get(user=transaction_instance.sender)
            recipient_user_stat = UserStat.objects.get(user=transaction_instance.recipient)
            recipient_income_account = recipient_accounts.filter(account_type='I').first()
            sender_frozen_account = sender_accounts.filter(account_type='F').first()
            sender_distr_account = sender_accounts.filter(account_type='D').first()
            amount = transaction_instance.amount
            if transaction_status == 'A':
                recipient_income_account.amount += amount
                recipient_user_stat.income_thanks += amount
            if transaction_status == 'D':
                sender_distr_account.amount += amount
                sender_user_stat.distr_redist += amount
                sender_user_stat.distr_thanks -= amount
                sender_user_stat.distr_declined += amount
            sender_frozen_account.amount -= amount
            recipient_income_account.transaction = transaction_instance
            sender_frozen_account.transaction = transaction_instance
            recipient_income_account.save()
            sender_frozen_account.save()
            sender_distr_account.save()
            sender_user_stat.save()
            recipient_user_stat.save()
            response.update({"transaction": transaction_pk, "status": transaction_status, "reason": reason})
    return response


def get_search_user_data(data, request):
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
    return users_data


def update_transaction_by_user(instance, request, serializer):
    with transaction.atomic():
        sender_accounts = instance.sender.accounts.all()
        amount = instance.amount
        sender_user_stat = UserStat.objects.get(user=request.user)
        sender_distr_account = sender_accounts.filter(account_type='D').first()
        sender_frozen_account = sender_accounts.filter(account_type='F').first()
        sender_distr_account.amount += amount
        sender_frozen_account.amount -= amount
        sender_user_stat.distr_redist += amount
        sender_user_stat.distr_thanks -= amount
        sender_distr_account.save()
        sender_frozen_account.save()
        serializer.save()
