import logging

from django.shortcuts import get_object_or_404
from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from utils.challenges_logic import (get_challenge_state_values, add_annotated_fields_to_challenges,
                                    update_challenge_photo_link_to_thumbnail,
                                    update_participant_photo_link_to_thumbnail,
                                    update_report_photo_link_to_thumbnail,
                                    update_challenge_photo_link, set_active_field, set_completed_field,
                                    calculate_remaining_top_places, update_time_in_challenges,
                                    update_time_in_winners_list, update_time_in_participants_list,
                                    check_if_new_reports_exists)

from auth_app.models import Challenge, ChallengeParticipant
from .serializers import CreateChallengeSerializer

logger = logging.getLogger(__name__)


class CreateChallengeView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Challenge.objects.all()
    serializer_class = CreateChallengeSerializer


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
