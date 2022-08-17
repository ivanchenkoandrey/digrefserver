from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from auth_app.models import Organization
from utils.custom_permissions import IsMemberOfAdminGroup
from .serializers import RootOrganizationSerializer


class CreateRootOrganization(CreateAPIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated, IsMemberOfAdminGroup]
    queryset = Organization.objects.all()
    serializer_class = RootOrganizationSerializer
