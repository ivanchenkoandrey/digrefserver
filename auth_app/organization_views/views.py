from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Organization
from utils.custom_permissions import IsSystemAdmin, IsDepartmentAdmin, IsOrganizationAdmin
from .serializers import (RootOrganizationSerializer,
                          DepartmentSerializer)


class CreateRootOrganization(CreateAPIView):
    """
    Создание организации верхнего уровня
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin]
    queryset = Organization.objects.all()
    serializer_class = RootOrganizationSerializer


class CreateDepartmentView(APIView):
    """
    Создание подразделения
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsOrganizationAdmin, IsDepartmentAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        data = request.data
        if data.get('parent_id') is None or data.get('top_id') is None:
            return Response('У подразделения должны быть parent_id '
                            '(вышестоящее подразделение) и top_id (юридическое лицо)',
                            status=status.HTTP_400_BAD_REQUEST)
        data.update({"organization_type": "D"})
        serializer = DepartmentSerializer(data=data, context={"request": request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
