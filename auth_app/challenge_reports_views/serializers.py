from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction as tr
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.comments_views.service import create_comment
from auth_app.models import (ChallengeReport, Event, EventTypes,
                             ChallengeParticipant, Account, Transaction, UserStat)
from auth_app.tasks import send_multiple_notifications
from utils.challenges_logic import check_if_new_reports_exists
from utils.crop_photos import crop_image
from utils.current_period import get_current_period
from utils.fcm_services import get_fcm_tokens_list
from utils.handle_image import change_filename
from utils.notification_services import get_notification_message_for_challenge_author_get_report, create_notification, \
    get_notification_message_for_challenge_winner
from utils.thumbnail_link import get_thumbnail_link

User = get_user_model()


class CreateChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['challenge', 'text']

    def create(self, validated_data):
        request = self.context.get('request')
        user = User.objects.select_related('profile').filter(pk=request.user.pk).first()
        challenge = validated_data['challenge']
        text = validated_data['text']
        photo = request.FILES.get('photo')
        with tr.atomic():

            try:
                participant = ChallengeParticipant.objects.get(challenge=challenge, user_participant=user)
                if 'K' in challenge.challenge_mode and 'P' in participant.mode:
                    raise ValidationError("Данный участник уже отправил отчет для этого челленджа")

                if 'O' in participant.mode:
                    raise ValidationError("Организатор не может участвовать в своем челлендже")

            except ChallengeParticipant.DoesNotExist:
                participant = ChallengeParticipant.objects.create(
                    user_participant=user,
                    challenge=challenge,
                    contribution=0,
                    mode=['A', 'P']
                )
                challenge.participants_count += 1
                challenge.save(update_fields=["participants_count"])

            challenge_report_instance = ChallengeReport.objects.create(
                participant=participant,
                challenge=challenge,
                text=text,
                state='S',
                photo=photo
            )
            if challenge_report_instance.photo.name is not None:
                challenge_report_instance.photo.name = change_filename(challenge_report_instance.photo.name)
                challenge_report_instance.save(update_fields=['photo'])
                crop_image(challenge_report_instance.photo.name, f"{settings.BASE_DIR}/media/", to_square=False)
            self.create_and_send_author_getting_reports_notifications(challenge, challenge_report_instance, user)
            return challenge_report_instance

    @staticmethod
    def create_and_send_author_getting_reports_notifications(challenge, challenge_report_instance, user):
        notification_data = {
            'report_sender_tg_name': user.profile.tg_name,
            'report_sender_photo': user.profile.get_thumbnail_photo_url,
            'report_sender_surname': user.profile.surname,
            'report_sender_first_name': user.profile.first_name,
            'challenge_id': challenge_report_instance.challenge_id,
            'challenge_name': challenge.name,
            'report_id': challenge_report_instance.pk
        }
        push_data = {key: str(value) for key, value in notification_data.items()}
        notification_theme, notification_text = get_notification_message_for_challenge_author_get_report(
            report_author_name=user.profile.tg_name, challenge_name=challenge.name
        )
        create_notification(
            challenge.creator_id,
            challenge_report_instance.pk,
            'R',
            notification_theme,
            notification_text,
            data=notification_data,
            from_user=challenge.creator_id
        )
        send_multiple_notifications.delay(
            notification_theme,
            notification_text,
            tokens=get_fcm_tokens_list(challenge.creator_id),
            data=push_data
        )


class CheckChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['state', 'text']

    def validate(self, validated_data):

        state = validated_data['state']
        text = self.instance.text
        reason = validated_data['text']
        validated_data['text'] = text
        challenge_report = self.instance
        user_participant = challenge_report.participant.user_participant
        reviewer = self.context['request'].user
        challenge_creator = challenge_report.challenge.creator

        if challenge_report.state in ['W', 'D']:
            raise ValidationError("Отчет уже отклонен или уже выдана награда")
        if reviewer != challenge_creator:
            raise ValidationError("Отправивший запрос не является создателем челленджа")
        if 'C' in challenge_report.challenge.states and state == 'W':
            raise ValidationError("Челлендж уже завершен")
        if (reason is not None and reason != '') and state == 'D':
            content_type = "ChallengeReport"
            create_comment(content_type, challenge_report.id, reason, None, reviewer, None, None, None, None, None)

        if state == 'W':
            with tr.atomic():
                challenge = challenge_report.challenge
                winners_count = challenge.winners_count
                challenge.winners_count = winners_count + 1
                challenge.save(update_fields=["winners_count"])

                if challenge.parameters[0]["id"] == 2:
                    max_winners = challenge.parameters[0]["value"]
                    prize = challenge.parameters[1]["value"]
                else:
                    max_winners = challenge.parameters[1]["value"]
                    prize = challenge.parameters[0]["value"]

                participant = ChallengeParticipant.objects.get(user_participant=user_participant, challenge=challenge)
                participant.total_received += prize
                participant.save(update_fields=['total_received'])

                sender_account = Account.objects.get(challenge=challenge, account_type='D')
                sender_account.amount -= prize
                recipient_account = Account.objects.get(owner=user_participant, account_type='I')
                recipient_account.amount += prize

                current_period = get_current_period()
                transaction = Transaction.objects.create(
                    is_anonymous=False,
                    sender_account=sender_account,
                    from_challenge=challenge,
                    recipient_account=recipient_account,
                    amount=prize,
                    transaction_class='W',
                    status='R',
                    period=current_period,
                    challenge_report=self.instance
                )
                Event.objects.create(
                    event_type=EventTypes.objects.get(name='Новый победитель челленджа'),
                    event_object_id=self.instance.pk,
                    object_selector='R',
                    time=datetime.now()
                )

                self.create_and_send_winner_report_notifications(challenge, challenge_report, prize, user_participant)

                sender_account.transaction = transaction
                sender_account.save(update_fields=['amount', 'transaction'])
                recipient_account.transaction = transaction
                recipient_account.save(update_fields=['amount', 'transaction'])

                receiver_user_stat = UserStat.objects.get(user=user_participant, period=current_period)
                receiver_user_stat.awarded_from_challenges += prize
                receiver_user_stat.save(update_fields=['awarded_from_challenges'])

                if max_winners == winners_count + 1:
                    challenge.states = ['P', 'C']
                    challenge.save(update_fields=["states"])

                    if sender_account.amount > 0:
                        remain = sender_account.amount
                        sender_account.amount -= remain
                        sender_account.save(update_fields=['amount'])
                        recipient_account = Transaction.objects.get(to_challenge=challenge).sender_account
                        transaction = Transaction.objects.create(
                            is_anonymous=False,
                            sender_account=sender_account,
                            from_challenge=challenge,
                            recipient_account=recipient_account,
                            amount=remain,
                            transaction_class='F',
                            status='R',
                            period=current_period,
                        )

                        participant = ChallengeParticipant.objects.get(user_participant=reviewer, challenge=challenge)
                        participant.total_received += remain
                        participant.save(update_fields=['total_received'])

                        user_stat = UserStat.objects.get(user=reviewer, period=current_period)
                        user_stat.returned_from_challenges += remain
                        user_stat.save(update_fields=['returned_from_challenges'])

                        recipient_account.transaction = transaction
                        recipient_account.amount += remain
                        recipient_account.save(update_fields=['amount', 'transaction'])

        new_reports_exists = check_if_new_reports_exists(reviewer)
        validated_data['new_reports_exists'] = new_reports_exists
        return {"state": state, 'new_reports_exists': new_reports_exists}

    @staticmethod
    def create_and_send_winner_report_notifications(challenge, challenge_report, prize, user_participant):
        notification_theme, notification_text = get_notification_message_for_challenge_winner(challenge.name)
        notification_data = {
            "challenge_id": challenge.pk,
            "challenge_name": challenge.name,
            "challenge_report_id": challenge_report.pk,
            "prize": prize
        }
        push_data = {key: str(value) for key, value in notification_data.items()}
        create_notification(
            user_participant.id,
            challenge_report.id,
            'W',
            notification_theme,
            notification_text,
            data=notification_data,
            from_user=challenge.creator_id
        )
        send_multiple_notifications.delay(
            notification_theme,
            notification_text,
            tokens=get_fcm_tokens_list(user_participant.id),
            data=push_data
        )


class ChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['challenge', 'user', 'text', 'photo']

    challenge = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()

    def get_challenge(self, obj):
        challenge = {
            "id": self.context.get('challenge').id,
            "name": self.context.get('challenge').name
        }
        return challenge

    def get_user(self, obj):
        avatar = self.context.get('user_profile').get_photo_url()
        user = {
            "id": self.context.get('user').id,
            "tg_name": self.context.get('user_profile').tg_name,
            "name": self.context.get('user_profile').first_name,
            "surname": self.context.get('user_profile').surname,
            'avatar': get_thumbnail_link(avatar) if avatar is not None else None
        }
        return user

    def get_text(self, obj):
        text = obj.text
        return text

    def get_photo(self, obj):
        if getattr(obj, "photo"):
            photo = obj.photo.url
        else:
            photo = None
        return photo
