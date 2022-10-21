from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from auth_app.models import ChallengeReport
from utils.challenges_logic import check_if_new_reports_exists
from utils.query_debugger import query_debugger
from .serializers import ChallengeReportSerializer
from .serializers import CreateChallengeReportSerializer, CheckChallengeReportSerializer


class CreateChallengeReportView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = ChallengeReport.objects.all()
    serializer_class = CreateChallengeReportSerializer


class CheckChallengeReportView(UpdateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = ChallengeReport.objects.all()
    serializer_class = CheckChallengeReportSerializer
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            new_reports_exists = check_if_new_reports_exists(request.user)
            return Response({"state": request.data['state'], "new_reports_exists": new_reports_exists})
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class ChallengeReportDetailAPIView(APIView):
    """
    Возвращает детали отчета
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    @query_debugger
    def get(cls, request, *args, **kwargs):
        pk = kwargs.get('pk')
        challenge_report = (ChallengeReport.objects
                            .select_related('challenge', 'participant__user_participant__profile')
                            .filter(pk=pk)
                            .only('challenge_id', 'challenge__name', 'text', 'photo',
                                  'participant__user_participant__id',
                                  'participant__user_participant__profile__tg_name',
                                  'participant__user_participant__profile__first_name',
                                  'participant__user_participant__profile__surname',
                                  'participant__user_participant__profile__photo')
                            .first())
        if challenge_report is not None:
            challenge = challenge_report.challenge
            participant = challenge_report.participant
            user = participant.user_participant
            context = {
                "challenge": challenge,
                "user": user,
                "user_profile": user.profile

            }
            serializer = ChallengeReportSerializer(challenge_report, context=context)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)
