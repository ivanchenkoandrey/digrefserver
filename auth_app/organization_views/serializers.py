import logging

from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import Organization
from utils.crop_photos import crop_image
from utils.handle_image import process_instance_image

logger = logging.getLogger(__name__)


class FullOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

    def get_photo(self, obj):
        if obj.photo:
            return obj.get_thumbnail_photo_url


class OrganizationImageSerializer(serializers.ModelSerializer):
    cropped_photo = serializers.ImageField(required=False)

    class Meta:
        model = Organization
        fields = ['photo', 'cropped_photo']

    def update(self, instance, validated_data):
        request = self.context.get('request')
        cropped_photo = request.FILES.get('cropped_photo')
        organization = super().update(instance, validated_data)
        process_instance_image(organization, cropped_photo)
        return organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['name', 'photo']


class RootOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['name', 'photo']

    def create(self, validated_data):
        name = validated_data['name']
        photo = validated_data['photo']
        with transaction.atomic():
            root_organization = Organization.objects.create(
                name=name,
                photo=photo,
                organization_type='R',
                top_id_id=1
            )
            root_organization.top_id = root_organization
            root_organization.save(update_fields=['top_id'])
            if root_organization.photo:
                crop_image(root_organization.photo.name, f"{settings.BASE_DIR}/media/")
        return root_organization


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['name', 'photo', 'top_id',
                  'parent_id', 'organization_type']

    def create(self, validated_data):
        top_organization = validated_data['top_id']
        top_ids = list(Organization.objects.filter(parent_id=None)
                       .values_list('pk', flat=True)
                       .distinct().order_by())
        top_id = top_organization.pk
        if top_id not in top_ids:
            raise ValidationError('Укажите в качестве top_id id какой-нибудь '
                                  'существующей ведущей компании')
        parent = validated_data['parent_id']
        possible_parent_ids = list(Organization.objects.filter(top_id=top_id)
                                   .values_list('pk', flat=True)
                                   .distinct().order_by())
        if parent.pk not in possible_parent_ids:
            raise ValidationError('Укажите в качестве parent_id свою ведущую компанию '
                                  'либо один из её департаментов')
        department = super().create(validated_data)
        if department.photo:
            crop_image(department.photo.name, f"{settings.BASE_DIR}/media/")
        return department
