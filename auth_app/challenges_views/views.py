import logging

from django.shortcuts import get_object_or_404
from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Challenge, ChallengeParticipant, ChallengeReport
from utils.challenge_queries import CHALLENGE_LIST_QUERY, CHALLENGE_PK_QUERY
from utils.challenges_logic import (get_challenge_state_values, add_annotated_fields_to_challenges,
                                    set_active_field, set_completed_field, calculate_remaining_top_places,
                                    check_if_new_reports_exists, set_names_to_null, get_challenge_report_status,
                                    update_link_on_thumbnail, update_time, update_photo_link,
                                    set_winner_nickname, reconfigure_challenges_queryset_into_dictionary)
from utils.query_debugger import query_debugger
from .service import create_challenge

logger = logging.getLogger(__name__)


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
        description = request.data.get('description', '')
        end_at = request.data.get('end_at')
        start_balance = int(request.data.get('start_balance'))
        parameter_id = request.data.get('parameter_id')
        parameter_value = request.data.get('parameter_value')
        photo = request.FILES.get('photo')

        response = create_challenge(creator, name, end_at, description, start_balance,  photo,
                                    parameter_id, parameter_value)

        return Response(response)


class ChallengeListView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    @query_debugger
    def get(cls, request, *args, **kwargs):
        active_only = request.GET.get('active_only')
        if cls.get_boolean_parameter(active_only):
            challenges = Challenge.objects.get_active_only(request.user.id)
        else:
            challenges = Challenge.objects.raw(
                CHALLENGE_LIST_QUERY, [request.user.id] * 7
            )
        challenges = reconfigure_challenges_queryset_into_dictionary(challenges)
        update_time(challenges, 'updated_at')
        add_annotated_fields_to_challenges(challenges)
        set_active_field(challenges)
        get_challenge_state_values(challenges)
        update_link_on_thumbnail(challenges, 'photo')
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
    @query_debugger
    def get(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        challenges = Challenge.objects.raw(
            CHALLENGE_PK_QUERY, [request.user.pk] * 7 + [pk]
        )
        if challenges:
            challenges = reconfigure_challenges_queryset_into_dictionary(challenges, pk=True)
            update_time(challenges, 'updated_at')
            add_annotated_fields_to_challenges(challenges)
            set_active_field(challenges)
            set_completed_field(challenges)
            get_challenge_state_values(challenges)
            update_photo_link(challenges, 'photo')
            update_link_on_thumbnail(challenges, 'creator_photo')
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
        challenge = get_object_or_404(Challenge, pk=pk)
        challenge_id = challenge.pk
        is_nickname_allowed = 'N' in challenge.challenge_mode
        winners = ChallengeParticipant.objects.get_winners_data(challenge_id)
        if is_nickname_allowed:
            set_names_to_null(winners)
        set_winner_nickname(winners)
        update_time(winners, 'awarded_at')
        update_link_on_thumbnail(winners, 'participant_photo')
        return Response(data=winners)


class ChallengeContendersList(APIView):
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
        is_nickname_allowed = 'N' in challenge.challenge_mode
        participants = ChallengeParticipant.objects.get_contenders_data(challenge_id)
        if is_nickname_allowed:
            set_names_to_null(participants)
        update_link_on_thumbnail(participants, 'participant_photo')
        update_link_on_thumbnail(participants, 'report_photo')
        update_time(participants, 'report_created_at')
        return Response(data=participants)


class CheckIfNewReportsExistView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        new_reports_exists = check_if_new_reports_exists(request.user.id)
        return Response({'is_exists': new_reports_exists})


class GetUserChallengeReportView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        reports = ChallengeReport.objects.get_user_challenge_result_data(request.user, pk)
        if reports:
            update_time(reports, 'updated_at')
            update_photo_link(reports, 'photo')
            for index in range(len(reports)):
                report_status = reports[index]['status']
                reports[index]['status'] = get_challenge_report_status(report_status)
            return Response(reports)
        return Response({'status': 'not found'}, status=status.HTTP_404_NOT_FOUND)
