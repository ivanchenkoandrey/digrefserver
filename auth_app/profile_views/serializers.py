import datetime
import logging
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import Contact, Profile, Organization, UserRole
from utils.handle_image import process_profile_image

PASSWORD = settings.DEFAULT_USER_PASSWORD
logger = logging.getLogger(__name__)

User = get_user_model()


class ProfileImageSerializer(serializers.ModelSerializer):
    cropped_photo = serializers.ImageField(required=False)

    class Meta:
        model = Profile
        fields = ['photo', 'cropped_photo']

    def update(self, instance, validated_data):
        request = self.context.get('request')
        cropped_photo = request.FILES.get('cropped_photo')
        profile = super().update(instance, validated_data)
        process_profile_image(profile, cropped_photo)
        return profile


class UserProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = ['tg_name', 'surname', 'first_name',
                  'middle_name', 'nickname', 'status',
                  'timezone', 'date_of_birth', 'job_title']

    def validate(self, attrs):
        date_of_birth = attrs.get('date_of_birth')
        if date_of_birth:
            today = datetime.date.today()
            if date_of_birth >= today:
                raise ValidationError('Укажите дату рождения в прошедшем времени')
        return attrs


class AdminProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = ['id', 'user', 'organization']

    def validate(self, attrs):
        hired_at = self.instance.hired_at
        fired_at = attrs.get('fired_at')
        organization = self.instance.organization
        department = attrs.get('department')
        if department:
            possible_departments = (list(Organization.objects.filter(top_id=organization.pk)
                                         .values_list('id', flat=True)
                                         .distinct().order_by()))
            if department.pk not in possible_departments:
                raise ValidationError('Передан ID, не относящийся к департаментам '
                                      'внутри организации работника')
        if hired_at and fired_at:
            if hired_at >= fired_at:
                raise ValidationError('Дата увольнения должна быть позже даты приема на работу')
        return attrs


class EmployeeSerializer(serializers.Serializer):
    tg_name = serializers.CharField()
    tg_id = serializers.CharField()
    organization_id = serializers.IntegerField()
    department_id = serializers.IntegerField()
    photo = serializers.ImageField(allow_null=True, required=False)
    surname = serializers.CharField(allow_null=True, required=False)
    first_name = serializers.CharField(allow_null=True, required=False)
    middle_name = serializers.CharField(allow_null=True, required=False)
    nickname = serializers.CharField(allow_null=True, required=False)
    hired_at = serializers.DateField(allow_null=True, required=False)
    phone_number = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    @classmethod
    def get_username_suffix(cls):
        return "".join([str(randint(0, 9)) for _ in range(4)])

    @classmethod
    def get_username(cls, tg_name, tg_id):
        return f"{tg_name}{tg_id}{cls.get_username_suffix()}"

    def create(self, validated_data):
        tg_name = validated_data['tg_name']
        tg_id = validated_data['tg_id']
        organization_id = validated_data['organization_id']
        department_id = validated_data['department_id']
        photo = self.context.get('request').FILES.get('photo')
        surname = self.data.get('surname')
        first_name = self.data.get('first_name')
        middle_name = self.data.get('middle_name')
        nickname = self.data.get('nickname')
        hired_at = self.data.get('hired_at')
        fired_at = self.data.get('fired_at')
        phone_number = self.data.get('phone_number')
        email = self.data.get('email')
        organization = Organization.objects.get(id=organization_id)
        possible_departments = (list(Organization.objects.filter(top_id=organization_id)
                                     .values_list('id', flat=True)
                                     .distinct().order_by()))
        if department_id not in possible_departments:
            raise ValidationError("Укажите существующий департамент "
                                  "в составе указанной вами организации")
        username = self.get_username(tg_name, tg_id)
        password = PASSWORD
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password
            )
            profile = Profile.objects.create(
                user=user,
                tg_name=tg_name,
                tg_id=tg_id,
                organization_id=organization_id,
                department_id=department_id,
                photo=photo,
                surname=surname,
                first_name=first_name,
                middle_name=middle_name,
                nickname=nickname,
                hired_at=hired_at,
                fired_at=fired_at,
            )
            if phone_number:
                Contact.objects.create(
                    profile=profile,
                    contact_type='P',
                    contact_id=phone_number,
                    confirmed=True
                )
            if email:
                Contact.objects.create(
                    profile=profile,
                    contact_type='@',
                    contact_id=email,
                    confirmed=True
                )
        return user


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'

    def create(self, validated_data):
        user_id = validated_data['user'].pk
        user_department_id = validated_data['user'].profile.department_id
        role = validated_data['role']
        department = validated_data['organization']
        if department is None:
            raise ValidationError("Не передано подразделение")
        department_id = department.pk
        if user_department_id != department_id:
            raise ValidationError("Пользователь может иметь роль в рамках своего подразделения")
        existing_user_role = UserRole.objects.filter(user_id=user_id, role=role).first()
        if existing_user_role is not None:
            raise ValidationError("Такая роль у этого пользователя уже задана")
        return super().create(validated_data)


class FullUserRoleSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    organization_id = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_id = serializers.SerializerMethodField()

    def get_organization(self, obj):
        organization = obj.organization
        if organization:
            return {"id": obj.organization.pk,
                    "name": obj.organization.name}
        return None

    def get_organization_id(self, obj):
        organization = obj.organization
        if organization:
            return obj.organization.pk
        return None

    def get_role(self, obj):
        return {"id": obj.id, "role": obj.role}

    def get_role_id(self, obj):
        return obj.id

    class Meta:
        model = UserRole
        exclude = ['user', 'id']
