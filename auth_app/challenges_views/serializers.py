from rest_framework import serializers
from auth_app.models import Challenge, Organization, Account
from rest_framework.exceptions import ValidationError
from utils.thumbnail_link import get_thumbnail_link
from utils.crop_photos import crop_image
from django.conf import settings
from utils.handle_image import change_challenge_filename
import logging
logger = logging.getLogger(__name__)


class CreateChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = ['name', 'description', 'end_at', 'start_balance', 'parameters', 'photo']

    def create(self, validated_data):
        creator = self.context['request'].user
        name = validated_data['name']
        description = validated_data['description']
        start_balance = validated_data['start_balance']
        parameters = validated_data['parameters']
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
            owner=creator, account_type='D').first()
        current_account_amount = sender_distr_account.amount
        from_income = False
        if current_account_amount == 0:
            sender_income_account = Account.objects.filter(
                owner=creator, account_type='I').first()
            current_account_amount = sender_income_account.amount
            from_income = True
        if current_account_amount - start_balance < 0:
            logger.info(f"Попытка {creator} создать челлендж с фондом на сумму больше имеющейся на счету")
            raise ValidationError("Нельзя добавить в фонд больше, чем есть на счету")
        if not from_income:
            sender_distr_account.amount -= start_balance
            # sender_user_stat.distr_thanks += start_balance
            sender_distr_account.save(update_fields=['amount'])
            # sender_user_stat.save(update_fields=['distr_thanks'])
        else:
            sender_income_account.amount -= start_balance
            # sender_user_stat.income_used_for_thanks += amount
            sender_income_account.save(update_fields=['amount'])
            # sender_user_stat.save(update_fields=['income_used_for_thanks'])
        challenge_instance = Challenge.objects.create(
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
        if challenge_instance.photo.name is not None:
            challenge_instance.photo.name = change_challenge_filename(challenge_instance.photo.name)
            challenge_instance.save(update_fields=['photo'])
            crop_image(challenge_instance.photo.name, f"{settings.BASE_DIR}/media/")
        return challenge_instance

