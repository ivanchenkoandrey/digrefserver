from __future__ import absolute_import, unicode_literals

import logging

from django.core.mail import send_mail
from django.core.management import call_command
from utils.query_debugger import query_debugger

from digrefserver.celery import app

logger = logging.getLogger(__name__)


@app.task
def send(user_email: str, code: str) -> None:
    send_mail(
        'Подтверждение входа в сервис Цифровое Спасибо',
        f'Вы запросили пароль для входа в сервис Цифровое спасибо.\nВаш код доступа: {code}',
        'test_mobile_thanks@mail.ru',
        [user_email],
        fail_silently=False,
    )


@app.task
def remove_reports():
    call_command('remove_reports')


@app.task
@query_debugger
def validate_transactions_after_grace_period():
    from auth_app.models import Account, Transaction, UserStat
    from django.conf import settings
    from django.db import transaction
    from datetime import datetime, timezone
    from utils.current_period import get_current_period

    grace_period = settings.GRACE_PERIOD
    now = datetime.now(timezone.utc)
    period = get_current_period()
    if period is None:
        return
    transactions_to_check = [t for t in Transaction.objects
                             .select_related('sender_account', 'recipient_account')
                             .filter(status='G')
                             .only('sender_id', 'recipient_id', 'status', 'amount',
                             'period', 'created_at', 'sender_account', 'recipient_account')]
    with transaction.atomic():
        accounts = Account.objects.only('owner_id', 'amount', 'account_type', 'transaction')
        user_stats = (UserStat.objects
                      .filter(period=period)
                      .only('period', 'income_thanks'))
        for _transaction in transactions_to_check:
            amount = _transaction.amount
            if (now - _transaction.created_at).seconds >= grace_period:
                sender_accounts = [account for account in accounts
                                   if account.owner_id == _transaction.sender_id]
                recipient_accounts = [account for account in accounts
                                      if account.owner_id == _transaction.recipient_id]
                recipient_user_stat = [stat for stat in user_stats
                                       if stat.user_id == _transaction.recipient_id][0]
                sender_frozen_account = [account for account in sender_accounts
                                         if account.account_type == 'F'][0]
                recipient_income_account = [account for account in recipient_accounts
                                            if account.account_type == 'I'][0]
                sender_frozen_account.amount -= amount
                sender_frozen_account.transaction = _transaction
                recipient_income_account.amount += amount
                recipient_income_account.transaction = _transaction
                recipient_user_stat.income_thanks += amount
                _transaction.status = 'R'
                _transaction.recipient_account = recipient_income_account
                _transaction.save(update_fields=['status', 'updated_at', 'recipient_account'])
                sender_frozen_account.save(update_fields=['amount', 'transaction'])
                recipient_income_account.save(update_fields=['amount', 'transaction'])
                recipient_user_stat.save(update_fields=['income_thanks'])
