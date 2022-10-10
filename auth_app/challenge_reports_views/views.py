from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from auth_app.models import ChallengeReport
from rest_framework.response import Response

from utils.challenges_logic import check_if_new_reports_exists
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
