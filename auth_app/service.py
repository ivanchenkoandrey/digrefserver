import logging
from dataclasses import dataclass
from typing import Dict, List, Union

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpRequest

from auth_app.models import Transaction, TransactionState, UserStat
from auth_app.serializers import TransactionCancelSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


class VerifyTransactionItemError(Exception):
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


def is_controller_data_is_valid(data: List[List[Union[int, str]]]) -> bool:
    """Проверка валидности запроса и формата данных,
    переданных в запросе на верификацию транзакций контроллером"""
    try:
        for item in data:
            _id, status, reason = item
            VerifyTransactionItem(_id, status, reason)
        return True
    except (TypeError, ValueError):
        logger.info(f"Неправильный запрос верификации транзакций контроллером: {data}")
        return False
    except VerifyTransactionItemError:
        logger.info(f"Неправильный формат данных, переданный "
                    f"запросом на верификацию транзакций контроллером: {data}")
        return False


def update_transactions_by_controller(data: Dict,
                                      request: HttpRequest) -> List[Dict]:
    """Обновление контроллером статусов транзакций, счетов пользователей и их статистики"""
    response = []
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
            transaction_instance.save(update_fields=['status'])
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


def cancel_transaction_by_user(instance: Transaction,
                               request: HttpRequest,
                               serializer: TransactionCancelSerializer) -> None:
    """
    Обновление статуса транзакции отправителем на Отменена,
    обновление данных счёта и статистики в рамках одной транзакции в БД
    """
    with transaction.atomic():
        sender_accounts = instance.sender.accounts.all()
        amount = instance.amount
        sender_user_stat = UserStat.objects.get(user=request.user)
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
