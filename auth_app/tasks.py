from __future__ import absolute_import, unicode_literals

import logging

from django.core.mail import send_mail

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
def validate_transactions_after_grace_period():
    from auth_app.models import Account, Transaction, UserStat
    from django.conf import settings
    from django.db import transaction
    from datetime import datetime, timezone

    grace_period = settings.GRACE_PERIOD
    now = datetime.now(timezone.utc)

    transactions_to_check = Transaction.objects.filter(status='G')
    with transaction.atomic():
        accounts = Account.objects.all()
        user_stats = UserStat.objects.all()
        for _transaction in transactions_to_check:
            amount = _transaction.amount
            if (now - _transaction.created_at).seconds >= grace_period:
                sender_accounts = accounts.filter(owner_id=_transaction.sender_id)
                recipient_accounts = accounts.filter(owner_id=_transaction.recipient_id)
                recipient_user_stat = user_stats.get(period=_transaction.period,
                                                     user_id=_transaction.recipient_id)
                sender_frozen_account = sender_accounts.get(account_type='F')
                recipient_income_account = recipient_accounts.get(account_type='I')
                sender_frozen_account.amount -= amount
                sender_frozen_account.transaction = _transaction
                recipient_income_account.amount += amount
                recipient_income_account.transaction = _transaction
                recipient_user_stat.income_thanks += amount
                _transaction.status = 'R'
                _transaction.save(update_fields=['status'])
                sender_frozen_account.save(update_fields=['amount', 'transaction'])
                recipient_income_account.save(update_fields=['amount', 'transaction'])
                recipient_user_stat.save(update_fields=['income_thanks'])
