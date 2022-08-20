from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Organization
from utils.custom_permissions import IsSystemAdmin, IsDepartmentAdmin, IsOrganizationAdmin
from .serializers import (RootOrganizationSerializer,
                          DepartmentSerializer,
                          FullOrganizationSerializer)


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


class RootOrganizationListView(ListAPIView):
    """
    Cписок организаций верхнего уровня
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin,
                          IsDepartmentAdmin]
    queryset = Organization.objects.filter(parent_id=None)
    serializer_class = FullOrganizationSerializer


class DepartmentsListView(APIView):
    """
    Список всех подразделений переданной организации
    """
    authentication_classes = [authentication.TokenAuthentication,
                              authentication.SessionAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin,
                          IsDepartmentAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        organization_id = request.data.get('organization_id')
        if organization_id is not None:
            try:
                root_organization = Organization.objects.get(pk=organization_id)
                departments = root_organization.children.all()
                serializer = FullOrganizationSerializer(departments, many=True)
                return Response(serializer.data)
            except Organization.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной организации",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр organization_id",
                        status=status.HTTP_400_BAD_REQUEST)
