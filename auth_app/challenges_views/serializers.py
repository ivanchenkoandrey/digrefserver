from rest_framework import serializers
from auth_app.models import Challenge, Organization, Account, UserStat, Transaction
from rest_framework.exceptions import ValidationError
from utils.thumbnail_link import get_thumbnail_link
from utils.crop_photos import crop_image
from django.conf import settings
from django.db import transaction as tr
from utils.handle_image import change_challenge_filename
import logging
from utils.current_period import get_current_period
logger = logging.getLogger(__name__)


class CreateChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = ['name', 'description', 'challenge_mode', 'end_at', 'start_balance', 'parameters', 'photo']

    def create(self, validated_data):
        creator = self.context['request'].user
        name = validated_data['name']
        description = validated_data['description']
        start_balance = validated_data['start_balance']
        parameters = validated_data['parameters']
        challenge_modes = validated_data['challenge_mode']

        request = self.context.get('request')
        photo = request.FILES.get('photo')
        if parameters is None:
            parameters = [{"id": 2, "value": 5},
                          {"id": 1, "value": start_balance // 5, "is_calc": True}]

        elif parameters[0]["id"] == 2:
            parameters.append({"id": 1, "value": start_balance // parameters[0]["value"], "is_calc": True})
        elif parameters[0]["id"] == 1:
            parameters.append({"id": 2, "value": start_balance // parameters[0]["value"], "is_calc": True})
        else:
            raise ValidationError("id в parameters должен принимать значение 1 или 2")
        validated_data['parameters'] = parameters

        sender_distr_account = Account.objects.filter(
            owner=creator, account_type='D', organization_id=None, challenge_id=None).first()
        current_account_amount = sender_distr_account.amount
        from_income = False
        account_to_save = sender_distr_account
        if current_account_amount == 0:
            sender_income_account = Account.objects.filter(
                owner=creator, account_type='I', organization_id=None, challenge_id=None).first()
            current_account_amount = sender_income_account.amount
            account_to_save = sender_income_account
            from_income = True
        if current_account_amount - start_balance < 0:
            logger.info(f"Попытка {creator} создать челлендж с фондом на сумму больше имеющейся на счету")
            raise ValidationError("Нельзя добавить в фонд больше, чем есть на счету")

        if not from_income:
            sender_distr_account.amount -= start_balance
            sender_distr_account.save(update_fields=['amount'])
        else:
            sender_income_account.amount -= start_balance
            sender_income_account.save(update_fields=['amount'])
        user_stat = UserStat.objects.get(user=creator)
        user_stat.sent_to_challenges += start_balance
        user_stat.save(update_fields=['sent_to_challenges'])
        with tr.atomic():
            challenge = Challenge.objects.create(
                creator=creator,
                organized_by=creator,
                name=name,
                description=description,
                states=['P'],
                challenge_mode=['P'],
                start_balance=start_balance,
                parameters=parameters,
                photo=photo
            )

            recipient_account = Account.objects.create(
                owner=creator,
                account_type='D',
                amount=start_balance,
                challenge=challenge,
            )

            current_period = get_current_period()
            transaction = Transaction.objects.create(
                is_anonymous=False,
                sender_account=account_to_save,
                to_challenge=challenge,
                recipient_account=recipient_account,
                amount=start_balance,
                status='R',
                period=current_period,

            )
            recipient_account.transaction = transaction
            recipient_account.save(update_fields=['transaction'])

            if challenge.photo.name is not None:
                challenge.photo.name = change_challenge_filename(challenge.photo.name)
                challenge.save(update_fields=['photo'])
                crop_image(challenge.photo.name, f"{settings.BASE_DIR}/media/")
            return challenge

