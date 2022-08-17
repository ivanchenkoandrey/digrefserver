from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Organization
from utils.custom_permissions import IsMemberOfAdminGroup
from .serializers import OrganizationSerializer


class CreateRootOrganization(APIView):
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated, IsMemberOfAdminGroup]

    @classmethod
    def post(cls, request, *args, **kwargs):
        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            top_organization = Organization.objects.create(
                name=serializer.validated_data['name'],
                organization_type='R'
            )
            top_organization.top_id = top_organization.pk
            top_organization.save(update_fields=['top_id'])
            response_data = top_organization.to_json()
            return Response(response_data, status=status.HTTP_201_CREATED)
