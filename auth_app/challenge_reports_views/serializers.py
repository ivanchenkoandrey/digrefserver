from django.conf import settings
from django.db import transaction as tr
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import ChallengeReport, ChallengeParticipant, Account, Transaction, UserStat
from utils.challenges_logic import check_if_new_reports_exists
from utils.crop_photos import crop_image
from utils.current_period import get_current_period
from utils.handle_image import change_filename


class CreateChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['challenge', 'text', 'photo']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        challenge = validated_data['challenge']
        text = validated_data['text']
        photo = request.FILES.get('photo')
        with tr.atomic():

            try:
                participant = ChallengeParticipant.objects.get(challenge=challenge, user_participant=user)
                if 'K' in challenge.challenge_mode:
                    raise ValidationError("Данный участник уже отправил отчет для этого челленджа")
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
            return challenge_report_instance


class CheckChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['state', 'reason']

    def validate(self, validated_data):

        state = validated_data['state']
        reason = validated_data['reason']
        challenge_report = self.instance
        user_participant = challenge_report.participant.user_participant
        reviewer = self.context['request'].user
        challenge_creator = challenge_report.challenge.creator
        if challenge_report.state in ['W', 'D']:
            raise ValidationError("Отчет уже отклонен или уже выдана награда")
        if reviewer != challenge_creator:
            raise ValidationError("Отправивший запрос не является создателем челленджа")
        if 'C' in challenge_report.challenge.states:
            raise ValidationError("Челлендж уже завершен")
        if reason is None and state == 'D':
            raise ValidationError("Не указана причина отклонения")
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
                )

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
                        sender_account.amount = 0
                        sender_account.save(update_fields='amount')
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
