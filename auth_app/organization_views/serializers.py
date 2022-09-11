import logging

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from auth_app.models import Organization

logger = logging.getLogger(__name__)


class FullOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


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
        root_organization = Organization.objects.create(
            name=name,
            photo=photo,
            organization_type='R',
            top_id_id=1
        )
        root_organization.top_id = root_organization
        root_organization.save(update_fields=['top_id'])
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
        if top_organization.pk not in top_ids:
            raise ValidationError('Укажите в качестве top_id id какой-нибудь '
                                  'существующей ведущей компании')
        parent = validated_data['parent_id']
        possible_parent_ids = list(Organization.objects.get(pk=top_organization.pk).children
                                   .values_list('pk', flat=True)
                                   .distinct().order_by()) + [top_organization.pk]
        if parent.pk not in possible_parent_ids:
            raise ValidationError('Укажите в качестве parent_id свою ведущую компанию '
                                  'либо один из её департаментов')
        return super().create(validated_data)
