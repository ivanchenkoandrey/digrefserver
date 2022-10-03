import logging

from django.shortcuts import get_object_or_404
from rest_framework import authentication, status
# from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from digrefserver import settings
from utils.challenges_logic import (get_challenge_state_values, add_annotated_fields_to_challenges,
                                    update_challenge_photo_link_to_thumbnail,
                                    update_participant_photo_link_to_thumbnail,
                                    update_report_photo_link_to_thumbnail,
                                    update_challenge_photo_link, set_active_field, set_completed_field,
                                    calculate_remaining_top_places, update_time_in_challenges,
                                    update_time_in_winners_list, update_time_in_participants_list,
                                    check_if_new_reports_exists)
from auth_app.models import Challenge, ChallengeParticipant, Transaction, Account, UserStat
from utils.crop_photos import crop_image
from utils.handle_image import change_challenge_filename
# from .serializers import CreateChallengeSerializer
from utils.current_period import get_current_period
from django.db import transaction as tr

logger = logging.getLogger(__name__)


# class CreateChallengeView(CreateAPIView):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [authentication.SessionAuthentication,
#                               authentication.TokenAuthentication]
#     queryset = Challenge.objects.all()
#     serializer_class = CreateChallengeSerializer


class CreateChallengeView(APIView):
    """
    Создание челленджа
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        creator = request.user
        name = request.data.get('name')
        description = request.data.get('description')
        start_balance = int(request.data.get('start_balance'))
        parameter_id = request.data.get('parameter_id')
        parameter_value = request.data.get('parameter_value')
        photo = request.FILES.get('photo')

        is_public = cls.get_boolean_parameter(request.data.get('is_public'))

        challenge_modes = []
        states = ['P']
        if is_public:
            challenge_modes.append('P')

        if parameter_id is None:
            parameters = [{"id": 2, "value": 5},
                          {"id": 1, "value": start_balance // 5, "is_calc": True}]
        else:
            if parameter_id != 1 or parameter_id != 2:
                raise ValidationError("parameter_id должен принимать значение 1 или 2")
            parameter_id = int(parameter_id)
            parameter_value = int(parameter_value)
            parameters = [{"id": parameter_id, "value": parameter_value},
                          {"id": 2/parameter_id, "value": start_balance // parameter_value, "is_calc": True}]

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
                states=states,
                challenge_mode=challenge_modes,
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
            return Response({"challenge_created": True})

    @classmethod
    def get_boolean_parameter(cls, parameter):
        if parameter is None:
            return False
        elif parameter in [1, '1', 'True', 'true']:
            return True
        return False


class ChallengeListView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        active_only = request.GET.get('active_only')
        if cls.get_boolean_parameter(active_only):
            challenges = Challenge.objects.get_active_only(request.user.id)
        else:
            challenges = Challenge.objects.get_all_challenges(request.user.id)
        update_time_in_challenges(challenges)
        add_annotated_fields_to_challenges(challenges)
        get_challenge_state_values(challenges)
        update_challenge_photo_link_to_thumbnail(challenges)
        return Response(data=challenges)

    @classmethod
    def get_boolean_parameter(cls, parameter):
        if parameter in ('1', 'true', 'True'):
            return True
        return False


class ChallengeDetailView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        challenges = Challenge.objects.get_challenge_by_pk(request.user.id, pk)
        if challenges:
            update_time_in_challenges(challenges)
            add_annotated_fields_to_challenges(challenges)
            set_active_field(challenges),
            set_completed_field(challenges),
            get_challenge_state_values(challenges)
            update_challenge_photo_link(challenges)
            calculate_remaining_top_places(challenges)
            return Response(challenges[0])
        return Response('Челлендж не найден', status=status.HTTP_404_NOT_FOUND)


class ChallengeWinnersList(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        challenge_id = get_object_or_404(Challenge, pk=pk).pk
        winners = ChallengeParticipant.objects.get_winners_data(challenge_id)
        update_time_in_winners_list(winners)
        update_participant_photo_link_to_thumbnail(winners)
        return Response(data=winners)


class ChallengeCandidatesList(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        challenge = get_object_or_404(Challenge, pk=pk)
        challenge_id = challenge.id
        if challenge.creator_id != request.user.id:
            return Response({'permission_denied': 'Вы не являетесь организатором челленджа'},
                            status=status.HTTP_403_FORBIDDEN)
        participants = ChallengeParticipant.objects.get_participants_data(challenge_id)
        update_participant_photo_link_to_thumbnail(participants)
        update_report_photo_link_to_thumbnail(participants)
        update_time_in_participants_list(participants)
        return Response(data=participants)


class CheckIfNewReportsExistView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        new_reports_exists = check_if_new_reports_exists(request.user.id)
        return Response({'is_exists': new_reports_exists})
