import logging

from django.contrib.auth import get_user_model
from rest_framework import authentication, status
from rest_framework.generics import UpdateAPIView, CreateAPIView, DestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Organization
from auth_app.models import Profile, UserRole
from utils.custom_permissions import (IsSystemAdmin, IsOrganizationAdmin,
                                      IsUserUpdatesHisProfile)
from .serializers import (EmployeeSerializer, UserRoleSerializer,
                          ProfileImageSerializer, FullUserRoleSerializer)

User = get_user_model()

logger = logging.getLogger(__name__)


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
        serializer = EmployeeSerializer(data=request.data, context={"request": request})
        try:
            if serializer.is_valid(raise_exception=True):
                serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Organization.DoesNotExist:
            return Response("Укажите существующую организацию", status=status.HTTP_400_BAD_REQUEST)


class CreateUserRoleView(CreateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer


class DeleteUserRoleView(DestroyAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer


class UserRoleListView(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if user_id is not None:
            roles = UserRole.objects.select_related('organization').filter(user_id=user_id)
            serializer = FullUserRoleSerializer(roles, many=True)
            return Response(serializer.data)
        return Response("Передайте ID работника для получения списка ролей",
                        status=status.HTTP_400_BAD_REQUEST)
