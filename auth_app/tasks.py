from __future__ import absolute_import, unicode_literals

import logging
from typing import List, Dict, Optional, Any

from django.core.mail import send_mail
from django.core.management import call_command

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
def send_multiple_notifications(title: str, msg: str, tokens: List[str], data: Dict[str, str]):
    from utils.fcm_manager import send_multiple_push
    send_multiple_push(
        title=title,
        msg=msg,
        tokens=tokens,
        data_object=data)


@app.task
def bulk_create_notifications(user_id_list: List[int],
                              object_id: int,
                              _type: str,
                              theme: str,
                              text: Optional[str],
                              read: bool = False,
                              data: Dict[str, Any] = '',
                              from_user: Optional[int] = None):
    from auth_app.models import Notification
    Notification.objects.bulk_create([
        Notification(
            user_id=user_id,
            from_user=from_user,
            object_id=object_id,
            type=_type,
            theme=theme,
            text=text,
            read=read,
            data=data
        ) for user_id in user_id_list])


@app.task
def validate_transactions_after_grace_period():
    from auth_app.models import (Account, Event, Transaction, EventTypes,
                                 TransactionState, UserStat)
    from django.conf import settings
    from django.db import transaction
    from datetime import datetime, timezone
    from utils.current_period import get_current_period
    from utils.fcm_manager import send_multiple_push
    from utils.fcm_services import get_fcm_tokens_list
    from utils.notification_services import (create_notification,
                                             get_notification_message_for_thanks_receiver,
                                             get_notification_data)

    grace_period = settings.GRACE_PERIOD
    now = datetime.now(timezone.utc)
    period = get_current_period()
    if period is None:
        return
    transactions_to_check = [t for t in Transaction.objects
    .select_related('sender_account', 'recipient_account',
                    'sender__profile', 'recipient__profile')
    .filter(status='G')
    .only('sender_id', 'recipient_id', 'sender__profile__first_name',
          'sender__profile__surname', 'recipient__profile__surname',
          'sender__profile__tg_name', 'recipient__profile__tg_name',
          'recipient__profile__surname', 'status', 'amount',
          'period', 'created_at', 'sender_account', 'recipient_account')]
    with transaction.atomic():
        accounts = (Account.objects.filter(organization_id=None, challenge_id=None)
                    .only('owner_id', 'amount', 'account_type', 'transaction'))
        user_stats = (UserStat.objects
                      .filter(period=period)
                      .only('user_id', 'period', 'income_thanks'))
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
                state = TransactionState.objects.create(transaction=_transaction, status='R')
                notification_theme_receiver, notification_text_receiver = get_notification_message_for_thanks_receiver(
                    sender_tg_name=_transaction.sender.profile.tg_name if not _transaction.is_anonymous else 'аноним',
                    amount=amount
                )
                receiver_notification_data = get_notification_data(_transaction)
                create_notification(
                    user_id=_transaction.recipient_id,
                    object_id=_transaction.id,
                    _type='T',
                    theme=notification_theme_receiver,
                    text=notification_text_receiver,
                    data=receiver_notification_data,
                    from_user=_transaction.sender_id
                )
                send_multiple_push(
                    notification_theme_receiver,
                    notification_text_receiver,
                    get_fcm_tokens_list(_transaction.recipient_id),
                    data_object={key: str(value) for key, value in receiver_notification_data.items()}
                )
                Event.objects.create(
                    event_type=EventTypes.objects.get(name='Новая публичная транзакция'),
                    event_record_id=state.pk,
                    event_object_id=_transaction.pk,
                    object_selector='T',
                    time=now
                )
                sender_frozen_account.save(update_fields=['amount', 'transaction'])
                recipient_income_account.save(update_fields=['amount', 'transaction'])
                recipient_user_stat.save(update_fields=['income_thanks'])
