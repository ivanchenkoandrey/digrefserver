from rest_framework import authentication
from rest_framework.generics import CreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated

from auth_app.models import Contact
from utils.custom_permissions import IsSystemAdmin, IsOrganizationAdmin
from .serializers import (AdminMakesContactSerializer,
                          UserMakesContactSerializer,
                          ContactFullSerializer)


class CreateContactView(CreateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Contact.objects.all()


class CreateContactByUserView(CreateContactView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserMakesContactSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user': self.request.user})
        return context


class CreateContactByAdminView(CreateContactView):
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]
    serializer_class = AdminMakesContactSerializer


class DeleteContactByAdmin(DestroyAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin, IsOrganizationAdmin]
    queryset = Contact.objects.all()
    serializer_class = ContactFullSerializer
