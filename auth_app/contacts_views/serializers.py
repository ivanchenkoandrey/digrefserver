from rest_framework import serializers
from auth_app.models import Contact
from rest_framework.exceptions import ValidationError


class UserMakesContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['profile', 'contact_type',
                  'contact_id']

    def create(self, validated_data):
        request_user_profile = self.context.get('user').profile
        if request_user_profile.pk != validated_data['profile'].pk:
            raise ValidationError("Пользователь может создать контакт только в своём профиле")
        current_contacts = Contact.objects.filter(
            profile=request_user_profile, contact_id=validated_data['contact_id']).exists()
        if current_contacts:
            raise ValidationError("Контакт с таким значением у вас уже создан")
        validated_data['confirmed'] = False
        return super().create(validated_data)


class AdminMakesContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['profile', 'contact_type',
                  'contact_id']

    def create(self, validated_data):
        validated_data['confirmed'] = True
        return super().create(validated_data)


class ContactFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
