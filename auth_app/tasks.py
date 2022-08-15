from __future__ import absolute_import, unicode_literals

import datetime
import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction

from digrefserver.celery import app

logger = logging.getLogger(__name__)


@app.task
def make_log_message():
    logger.info(f'Task successfully done')


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
def open_period():
    User = get_user_model()
    today = datetime.date.today()
    from auth_app.models import Account, Transaction, Period
    period = Period.objects.filter(start_date=today).first()
    system_user = User.objects.get(accounts__account_type='S')
    organization = period.organization or None
    if period is not None:
        system_account = Account.objects.get(owner=system_user, type='S')
        users = User.objects.filter(profile__organization=period.organization).values_list('pk', flat=True)
        income_accounts = Account.objects.filter(account_type='I', owner_id__in=users)
        distr_accounts = Account.objects.filter(account_type='D', owner_id__in=users)
        with transaction.atomic():
            for account in income_accounts:
                Transaction.objects.create(
                    sender=system_user,
                    recipient=account.owner,
                    transaction_class='X',
                    amount=100,
                    status='R',
                    organization=organization
                )
                system_account.amount -= 100
            for account in distr_accounts:
                Transaction.objects.create(
                    sender=system_user,
                    recipient=account.owner,
                    transaction_class='D',
                    amount=100,
                    status='R',
                    organization=organization
                )
                system_account.amount -= 100
            system_account.save(update_fields=['amount'])
