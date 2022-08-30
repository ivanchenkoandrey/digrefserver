from rest_framework import authentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Contact
from auth_app.serializers import ContactUpdateSerializer
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
    permission_classes = [IsSystemAdmin | IsOrganizationAdmin]
    serializer_class = AdminMakesContactSerializer


class DeleteContactByAdmin(DestroyAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin | IsOrganizationAdmin]
    queryset = Contact.objects.all()
    serializer_class = ContactFullSerializer


class CreateFewContactsByUser(APIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def post(cls, request, *args, **kwargs):
        if cls.validate_request_data(request.data):
            cls.create_or_update_contacts(request)
            return Response(request.data)

    @classmethod
    def validate_request_data(cls, data):
        errors_list = []
        if not isinstance(data, list):
            raise ValidationError('Передайте на вход список структур контактов')
        for contact_item in data:
            if contact_item.get('contact_type') is None:
                errors_list.append('Проверьте, что в структуре передали contact_type')
            if contact_item.get('contact_id') is None:
                errors_list.append('Проверьте, что в структуре передали contact_id')
        if errors_list:
            raise ValidationError(errors_list)
        return True

    @classmethod
    def create_or_update_contacts(cls, request):
        data = request.data
        user_contacts = request.user.profile.contacts.all()
        existing_contact_ids = user_contacts.values_list('id', flat=True)
        for contact_item in data:
            contact_id = contact_item.get('contact_id')
            contact_pk = contact_item.get('id')
            if contact_pk is None:
                cls.create_contact(contact_item, request)
            else:
                cls.update_contact(contact_id, contact_pk, existing_contact_ids, user_contacts)

    @classmethod
    def update_contact(cls, contact_id, contact_pk, existing_contact_ids, user_contacts):
        if contact_pk in existing_contact_ids:
            if contact_id == "":
                user_contacts.get(pk=contact_pk).delete()
            else:
                instance = user_contacts.get(pk=contact_pk)
                serializer = ContactUpdateSerializer(
                    instance=instance,
                    data={'contact_id': contact_id},
                    partial=True)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
        else:
            raise ValidationError(f'Вы не можете обновить контакт с id {contact_pk}')

    @classmethod
    def create_contact(cls, contact_item, request):
        contact_item.update({'profile': request.user.profile.pk})
        serializer = UserMakesContactSerializer(context={'user': request.user}, data=contact_item)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
