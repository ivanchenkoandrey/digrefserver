from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from auth_app.models import Challenge
from .serializers import CreateChallengeSerializer


class CreateChallengeView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Challenge.objects.all()
    serializer_class = CreateChallengeSerializer
