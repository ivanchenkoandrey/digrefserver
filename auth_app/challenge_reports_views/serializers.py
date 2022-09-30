from rest_framework import serializers
from auth_app.models import ChallengeReport, Organization, ChallengeParticipant
from rest_framework.exceptions import ValidationError
from utils.thumbnail_link import get_thumbnail_link
from utils.crop_photos import crop_image
from django.conf import settings
from utils.handle_image import change_challenge_report_filename


class CreateChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['challenge', 'text', 'photo']

    def create(self, validated_data):
        participant = ChallengeParticipant.objects.get(user_participant=self.context['request'].user)

        challenge = validated_data['challenge']
        text = validated_data['text']

        request = self.context.get('request')
        photo = request.FILES.get('photo')

        challenge_report_instance = ChallengeReport.objects.create(
            participant=participant,
            challenge=challenge,
            text=text,
            state='W',
            photo=photo
        )
        is_new_reports = True
        if challenge_report_instance.photo.name is not None:
            challenge_report_instance.photo.name = change_challenge_report_filename(challenge_report_instance.photo.name)
            challenge_report_instance.save(update_fields=['photo'])
            crop_image(challenge_report_instance.photo.name, f"{settings.BASE_DIR}/media/")
        return challenge_report_instance, {'is_new_reports': is_new_reports}


class CheckChallengeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeReport
        fields = ['state']

    def validate(self, validated_data):
        id = self.instance.id
        state = validated_data['state']
        challenge_report = ChallengeReport.objects.get(id=id)
        reviewer = self.context['request'].user
        challenge_creator = challenge_report.challenge.creator
        text = 'Причина'
        if reviewer != challenge_creator:
            raise ValidationError("Отправивший запрос не является создателем челленджа")
        if 'C' in challenge_report.challenge.states:
            raise ValidationError("Челлендж уже завершен")
        if (text is None or text == '') and state == 'D':
            raise ValidationError("Не указана причина отклонения")
        # TODO update statistics?
        is_new_reports = True
        # challenge_report_data = {'state': state}
        # super().update(challenge_report, challenge_report_data)
        return validated_data, {'is_new_reports': is_new_reports}

