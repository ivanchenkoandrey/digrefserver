import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction as tr
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from auth_app.models import (Account, Event, Challenge, UserStat,
                             ChallengeParticipant, Transaction,
                             EventTypes, Profile, FCMToken)
from auth_app.tasks import bulk_create_notifications
from auth_app.tasks import send_multiple_notifications
from utils.crop_photos import crop_image
from utils.current_period import get_current_period
from utils.handle_image import change_filename
from utils.notification_services import get_notification_message_for_created_challenge

logger = logging.getLogger(__name__)
User = get_user_model()


def create_challenge(creator, name, end_at, description, start_balance, photo, parameter_id, parameter_value):
    period = get_current_period()

    if end_at == "":
        end_at = None

    if period is None:
        raise ValidationError("Сейчас нет активного периода")

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
        create_challenge_notifications(challenge, creator, name)
        return {"challenge_created": True}


def create_challenge_notifications(challenge, creator, name):
    creator_item = (Profile.objects.filter(user=creator)
                    .only('tg_name', 'first_name', 'surname', 'photo', 'organization_id')
                    .first())
    creator_data = {
        "tg_name": creator_item.tg_name,
        "first_name": creator_item.first_name,
        "surname": creator_item.surname,
        "photo": creator_item.get_thumbnail_photo_url,
        "organization_id": creator_item.organization_id
    }
    notification_data = get_creating_challenge_notification_data(challenge, creator_data, name)
    push_data = {key: str(value) for key, value in notification_data.items()}
    notification_theme, notification_message = get_notification_message_for_created_challenge(
        name, creator_data.get('tg_name'))
    users_id_to_notify_list = [user.id for user in User.objects.filter(
        Q(profile__organization_id=challenge.to_hold_id) |
        Q(profile__organization_id=creator_data.get('organization_id'))).only('id')
                               if user.id != creator.id]
    tokens = [fcm.token for fcm
              in FCMToken.objects
              .filter(user_id__in=users_id_to_notify_list)
              .only('token')]
    bulk_create_notifications.delay(
        user_id_list=users_id_to_notify_list,
        object_id=challenge.pk,
        _type='H',
        theme=notification_theme,
        text=notification_message,
        from_user=creator.id,
        data=notification_data
    )
    send_multiple_notifications.delay(
        title=notification_theme,
        msg=notification_message,
        tokens=tokens,
        data=push_data
    )


def get_creating_challenge_notification_data(challenge, creator_data, name):
    return {
        "creator_tg_name": creator_data.get('tg_name'),
        "creator_first_name": creator_data.get('first_name'),
        "creator_surname": creator_data.get('surname'),
        "creator_photo": creator_data.get('photo'),
        "challenge_name": name,
        "challenge_id": challenge.pk
    }
