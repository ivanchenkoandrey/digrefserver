import logging
from dataclasses import dataclass
from typing import Dict, List

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, F
from django.db.models.query import QuerySet
from django.http import HttpRequest
from rest_framework.exceptions import ValidationError

from auth_app.models import (Transaction, TransactionState, UserStat,
                             Account, Notification)
from auth_app.serializers import TransactionCancelSerializer
from utils.current_period import get_period, get_current_period
from utils.notification_services import update_transaction_status_in_sender_notification
from utils.thumbnail_link import get_thumbnail_link

User = get_user_model()

logger = logging.getLogger(__name__)


class VerifyTransactionItemError(Exception):
    pass


class AlreadyUpdatedByControllerError(Exception):
    pass


class NotWaitingTransactionError(Exception):
    pass


@dataclass
class VerifyTransactionItem:
    """Объект для быстрой проверки валидности входных данных
    по запросу верификации транзакций контролёром"""
    transaction_id: int
    transaction_status: str
    reason: str

    def __post_init__(self):
        if not isinstance(self.transaction_id, int):
            raise VerifyTransactionItemError("Первичный ключ транзакции должен быть числом!")
        if self.transaction_status not in ["A", "D"]:
            raise VerifyTransactionItemError("Статус должен быть либо A (одобрено), либо D (отклонено)")
        if not self.reason and self.transaction_status == 'D':
            raise VerifyTransactionItemError("Нужно указать обоснование смены статуса транзакции")


def is_controller_data_is_valid(data) -> bool:
    """Проверка валидности запроса и формата данных,
    переданных в запросе на верификацию транзакций контроллером"""
    try:
        for item in data:
            _id, status, reason = item.get('id'), item.get('status'), item.get('reason')
            VerifyTransactionItem(_id, status, reason)
        return True
    except (AttributeError, TypeError, ValueError):
        logger.info(f"Неправильный запрос верификации транзакций контроллером: {data}")
        return False
    except VerifyTransactionItemError:
        logger.info(f"Неправильный формат данных, переданный "
                    f"запросом на верификацию транзакций контроллером: {data}")
        return False


def update_transactions_by_controller(data: Dict,
                                      request: HttpRequest) -> List[Dict]:
    """Обновление контроллером статусов транзакций, счетов пользователей и их статистики"""
    period = get_period()
    waiting_transactions = {_transaction.id: _transaction
                            for _transaction in Transaction.objects.only(
                                    'id', 'status', 'reason', 'updated_at',
                                    'is_public', 'sender', 'recipient')}
    waiting_transactions_ids = {_object.id for _object in waiting_transactions}

    sender_recipient_ids = set()
    for item in data:
        if current_id := item.get('id') not in waiting_transactions_ids:
            raise ValidationError(f'Нет транзакции, '
                                  f'ожидающей подтверждения, с ID {current_id}')
        sender_recipient_ids.add(waiting_transactions.get(current_id).sender_id)
        sender_recipient_ids.add(waiting_transactions.get(current_id).recipient_id)

    accounts = {(account.owner_id, account.account_type): account
                for account in Account.objects.filter(organization_id=None, challenge_id=None,
                                                      owner_id__in=sender_recipient_ids).only(
                        'account_type', 'amount', 'owner_id', 'transaction')}
    user_stats = {stat.user_id: stat
                  for stat in UserStat.objects.filter(period=period, user_id__in=sender_recipient_ids).only(
                        'user_id', 'income_thanks', 'distr_thanks', 'distr_declined')}
    response = []
    with transaction.atomic():
        for transaction_data in data:
            transaction_pk = transaction_data.get('id')
            transaction_status = transaction_data.get('status')
            reason = transaction_data.get('reason')
            if not reason:
                reason = 'OK'
            transaction_instance = waiting_transactions.get(transaction_pk)
            TransactionState.objects.create(
                transaction=transaction_instance,
                controller=request.user,
                status=transaction_status,
                reason=reason
            )
            transaction_instance.status = transaction_status
            transaction_instance.is_public = True if transaction_status == 'A' else False
            transaction_instance.save(update_fields=['status', 'updated_at', 'is_public'])
            sender_user_stat = user_stats.get(transaction_instance.sender_id)
            recipient_user_stat = user_stats.get(transaction_instance.recipient_id)
            recipient_income_account = accounts.get((transaction_instance.recipient_id, 'I'))
            sender_frozen_account = accounts.get((transaction_instance.sender_id, 'F'))
            sender_distr_account = accounts.get((transaction_instance.sender_id, 'D'))
            amount = transaction_instance.amount
            if transaction_status == 'A':
                recipient_income_account.amount += amount
                recipient_user_stat.income_thanks += amount
                recipient_user_stat.save(update_fields=['income_thanks'])
            if transaction_status == 'D':
                sender_distr_account.amount += amount
                sender_user_stat.distr_thanks -= amount
                sender_user_stat.distr_declined += amount
                sender_user_stat.save(update_fields=['distr_thanks', 'distr_declined'])
            sender_frozen_account.amount -= amount
            recipient_income_account.transaction = transaction_instance
            sender_frozen_account.transaction = transaction_instance
            sender_distr_account.transaction = transaction_instance
            recipient_income_account.save(update_fields=['amount', 'transaction'])
            sender_frozen_account.save(update_fields=['amount', 'transaction'])
            sender_distr_account.save(update_fields=['amount', 'transaction'])
            response.append({"transaction": transaction_pk, "status": transaction_status, "reason": reason})
    return response


def get_search_user_data(data: Dict, request: HttpRequest) -> Dict:
    """Поиск пользователя по совпадению с началом запрошенной строки
    с именем, фамилией, никнеймом или адресом электронной почты"""
    main_search_filters = (Q(profile__tg_name__istartswith=data) |
                           Q(profile__first_name__istartswith=data) |
                           Q(profile__surname__istartswith=data) |
                           Q(profile__contacts__contact_id__istartswith=data))
    not_show_myself_filter = ~Q(profile__tg_name=request.user.profile.tg_name)
    not_show_system_filter = ~Q(username='system')
    if request.data.get('show_myself') is True:
        users_data = User.objects.filter(
            main_search_filters & not_show_system_filter).distinct()
    else:
        users_data = User.objects.filter(
            main_search_filters & not_show_myself_filter & not_show_system_filter).distinct()
    users_list = annotate_search_users_queryset(users_data)
    for user in users_list:
        photo = user.get('photo')
        if photo is not None:
            user['photo'] = get_thumbnail_link(photo)
    return users_list


def annotate_search_users_queryset(users_queryset: QuerySet) -> Dict:
    """Добавить поля с определённым названием для вывода JSON структуры"""
    return users_queryset.annotate(
        user_id=F('id'),
        profile_id=F('profile__id'),
        tg_name=F('profile__tg_name'),
        name=F('profile__first_name'),
        surname=F('profile__surname'),
        photo=F('profile__photo')).values(
        'user_id', 'profile_id', 'tg_name', 'name', 'surname', 'photo')[:10]


def cancel_transaction_by_user(instance: Transaction,
                               request: HttpRequest,
                               serializer: TransactionCancelSerializer) -> None:
    """
    Обновление статуса транзакции отправителем на Отменена,
    обновление данных счёта и статистики в рамках одной транзакции в БД
    """
    with transaction.atomic():
        period = get_current_period()
        amount = instance.amount
        account_to_return = instance.sender_account
        sender_user_stat = UserStat.objects.get(user=request.user, period=period)
        sender_frozen_account = instance.sender.accounts.filter(organization_id=None, challenge_id=None,
                                                                account_type='F').only('amount').first()
        account_to_return.amount += amount
        sender_frozen_account.amount -= amount
        if account_to_return.account_type == 'D':
            sender_user_stat.distr_thanks -= amount
            sender_user_stat.distr_declined += amount
            sender_user_stat.save(update_fields=['distr_thanks', 'distr_declined'])
        elif account_to_return.account_type == 'I':
            sender_user_stat.income_declined += amount
            sender_user_stat.income_used_for_thanks -= amount
            sender_user_stat.save(update_fields=['income_declined', 'income_used_for_thanks'])
        account_to_return.save(update_fields=['amount'])
        sender_frozen_account.save(update_fields=['amount'])
        serializer.save()


def is_cancel_transaction_request_is_valid(request_data: Dict) -> bool:
    """
    Валидация пришедших в запрос данных для отмены транзакции со стороны пользователя
    """
    if request_data.get('status') in ['D', 'C'] and len(request_data) == 1:
        return True
    return False
