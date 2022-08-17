from rest_framework import authentication
from rest_framework.generics import CreateAPIView

from auth_app.models import Organization
from utils.custom_permissions import IsSystemAdmin
from .serializers import RootOrganizationSerializer


class CreateRootOrganization(CreateAPIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin]
    queryset = Organization.objects.all()
    serializer_class = RootOrganizationSerializer
