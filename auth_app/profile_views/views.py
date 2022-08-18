import logging

from django.contrib.auth import get_user_model
from rest_framework import authentication, status
from rest_framework import serializers
from rest_framework.generics import UpdateAPIView
from rest_framework.views import APIView

from rest_framework.response import Response

from auth_app.models import Profile
from auth_app.serializers import CreateUserSerializer
from utils.custom_permissions import IsSystemAdmin, IsOrganizationAdmin, IsUserUpdatesHisProfile

User = get_user_model()

logger = logging.getLogger(__name__)


class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['photo']


class UpdateProfileImageView(UpdateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsUserUpdatesHisProfile]
    serializer_class = ProfileImageSerializer
    lookup_field = 'pk'

    def get_queryset(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        queryset = Profile.objects.filter(pk=pk)
        return queryset


class CreateEmployeeView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        username = request.data.get('username')
        user_serializer = CreateUserSerializer(data={"username": username})
        if user_serializer.is_valid(raise_exception=True):
            user_serializer.save()
            return Response(user_serializer.data, status=status.HTTP_201_CREATED)
