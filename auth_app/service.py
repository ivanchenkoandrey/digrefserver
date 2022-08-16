import logging
from dataclasses import dataclass
from typing import Dict, List

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpRequest

from auth_app.models import Transaction, TransactionState, UserStat
from auth_app.serializers import TransactionCancelSerializer
from utils.current_period import get_current_period

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
        if not self.reason:
            raise VerifyTransactionItemError("Нужно указать обоснование смены статуса транзакции")


def is_controller_data_is_valid(data) -> bool:
    """Проверка валидности запроса и формата данных,
    переданных в запросе на верификацию транзакций контроллером"""
    try:
        for item in data:
            logger.info(item)
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
    waiting_transactions_ids = (Transaction.objects
                                .filter(status='W')
                                .values_list('pk', flat=True))
    already_updated_ids = []
    response = []
    period = get_current_period()
    with transaction.atomic():
        for transaction_data in data:
            transaction_pk = transaction_data.get('id')
            if transaction_pk in already_updated_ids:
                raise AlreadyUpdatedByControllerError
            if transaction_pk not in waiting_transactions_ids:
                raise NotWaitingTransactionError
            transaction_status = transaction_data.get('status')
            reason = transaction_data.get('reason')
            transaction_instance = Transaction.objects.get(pk=transaction_pk)
            TransactionState.objects.create(
                transaction=transaction_instance,
                controller=request.user,
                status=transaction_status,
                reason=reason
            )
            transaction_instance.status = transaction_status
            transaction_instance.is_public = True if transaction_status == 'A' else False
            transaction_instance.save(update_fields=['status', 'updated_at', 'is_public'])
            sender_accounts = transaction_instance.sender.accounts.all()
            recipient_accounts = transaction_instance.recipient.accounts.all()
            sender_user_stat = UserStat.objects.get(user=transaction_instance.sender, period=period)
            recipient_user_stat = UserStat.objects.get(user=transaction_instance.recipient, period=period)
            recipient_income_account = recipient_accounts.filter(account_type='I').first()
            sender_frozen_account = sender_accounts.filter(account_type='F').first()
            sender_distr_account = sender_accounts.filter(account_type='D').first()
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
            already_updated_ids.append(transaction_pk)
    return response


def get_search_user_data(data: Dict, request: HttpRequest) -> Dict:
    """Поиск пользователя по совпадению с началом запрошенной строки
    с именем, фамилией, никнеймом или адресом электронной почты"""
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
        surname=F('profile__surname')).values('user_id', 'tg_name', 'name', 'surname')[:10]
    return users_data


def cancel_transaction_by_user(instance: Transaction,
                               request: HttpRequest,
                               serializer: TransactionCancelSerializer) -> None:
    """
    Обновление статуса транзакции отправителем на Отменена,
    обновление данных счёта и статистики в рамках одной транзакции в БД
    """
    with transaction.atomic():
        period = get_current_period()
        sender_accounts = instance.sender.accounts.all()
        amount = instance.amount
        sender_user_stat = UserStat.objects.get(user=request.user, period=period)
        sender_distr_account = sender_accounts.filter(account_type='D').first()
        sender_frozen_account = sender_accounts.filter(account_type='F').first()
        sender_distr_account.amount += amount
        sender_frozen_account.amount -= amount
        sender_user_stat.distr_thanks -= amount
        sender_user_stat.distr_declined += amount
        sender_distr_account.save(update_fields=['amount'])
        sender_frozen_account.save(update_fields=['amount'])
        sender_user_stat.save(update_fields=['distr_thanks', 'distr_declined'])
        serializer.save()


def is_cancel_transaction_request_is_valid(request_data: Dict) -> bool:
    """
    Валидация пришедших в запрос данных для отмены транзакции со стороны пользователя
    """
    if request_data.get('status') == 'D' and len(request_data) == 1:
        return True
    return False
