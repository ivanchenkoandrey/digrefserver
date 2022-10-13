import logging
from datetime import datetime

from django.conf import settings
from django.db import transaction as tr
from rest_framework.exceptions import ValidationError

from auth_app.models import (Account, Event, Challenge, UserStat,
                             ChallengeParticipant, Transaction, EventTypes)
from utils.crop_photos import crop_image
from utils.current_period import get_current_period
from utils.handle_image import change_filename

logger = logging.getLogger(__name__)


def create_challenge(creator, name, end_at, description, start_balance, photo, parameter_id, parameter_value):
    period = get_current_period()

    if period is None:
        raise ValidationError("Сейчас нет активного периода")
    try:
        end_at_date = datetime.strptime(end_at, '%Y-%m-%d')
    except ValueError:
        raise ValidationError(f"{end_at} не соответствует формату 'ГГГГ-ММ-ДД'")
    present = datetime.now()
    if end_at_date < present:
        raise ValidationError("Нельзя поставить дату завершения челленжа в прошедшем времени")
    challenge_modes = ['P']
    states = ['P']

    if parameter_id is None:
        parameters = [{"id": 2, "value": 5},
                      {"id": 1, "value": start_balance // 5, "is_calc": True}]
    else:
        parameter_id = int(parameter_id)
        parameter_value = int(parameter_value)
        if parameter_id == 2:
            if parameter_value > start_balance:
                parameter_value = start_balance
        if parameter_id != 1 and parameter_id != 2:
            raise ValidationError("parameter_id должен принимать значение 1 или 2")
        parameters = [{"id": parameter_id, "value": parameter_value},
                      {"id": 2 / parameter_id, "value": start_balance // parameter_value, "is_calc": True}]

    sender_distr_account = Account.objects.filter(
        owner=creator, account_type='D', organization_id=None, challenge_id=None).first()
    current_account_amount = sender_distr_account.amount
    from_income = False
    account_to_save = sender_distr_account
    if current_account_amount - start_balance < 0:
        sender_income_account = Account.objects.filter(
            owner=creator, account_type='I', organization_id=None, challenge_id=None).first()
        current_account_amount = sender_income_account.amount
        account_to_save = sender_income_account
        from_income = True
    if current_account_amount - start_balance < 0:
        logger.info(f"Попытка {creator} создать челлендж с фондом на сумму больше имеющейся на счету")
        raise ValidationError("Нельзя добавить в фонд больше, чем есть на счету")

    with tr.atomic():
        user_stat = UserStat.objects.get(user=creator, period=period)
        if not from_income:
            sender_distr_account.amount -= start_balance
            user_stat.sent_to_challenges += start_balance
            sender_distr_account.save(update_fields=['amount'])
            user_stat.save(update_fields=['sent_to_challenges'])
        else:
            sender_income_account.amount -= start_balance
            user_stat.sent_to_challenges_from_income += start_balance
            sender_income_account.save(update_fields=['amount'])
            user_stat.save(update_fields=['sent_to_challenges_from_income'])

        challenge = Challenge.objects.create(
            creator=creator,
            organized_by=creator,
            name=name,
            description=description,
            end_at=end_at,
            states=states,
            challenge_mode=challenge_modes,
            start_balance=start_balance,
            parameters=parameters,
            photo=photo
        )

        if 'P' in challenge.states:
            Event.objects.create(
                event_type=EventTypes.objects.get(name='Создан челлендж'),
                event_object_id=challenge.pk,
                object_selector='Q',
                time=datetime.now()
            )

        participant = ChallengeParticipant.objects.create(
            user_participant=creator,
            challenge=challenge,
            register_time=datetime.now(),
            contribution=start_balance,
            mode=['A', 'O']
        )
        recipient_account = Account.objects.create(
            owner=creator,
            account_type='D',
            amount=start_balance,
            challenge=challenge,
        )

        transaction = Transaction.objects.create(
            is_anonymous=False,
            sender_account=account_to_save,
            to_challenge=challenge,
            recipient_account=recipient_account,
            amount=start_balance,
            transaction_class='H',
            status='R',
            period=period,
        )
        recipient_account.transaction = transaction
        recipient_account.save(update_fields=['transaction'])
        if challenge.photo.name is not None:
            challenge.photo.name = change_filename(challenge.photo.name)
            challenge.save(update_fields=['photo'])
            crop_image(challenge.photo.name, f"{settings.BASE_DIR}/media/", to_square=False)
        return {"challenge_created": True}
