from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from auth_app.models import Challenge
from auth_app.serializers import CommentTransactionSerializer
from rest_framework.response import Response
from .serializers import CreateChallengeSerializer


class CreateChallengeView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Challenge.objects.all()
    serializer_class = CreateChallengeSerializer
