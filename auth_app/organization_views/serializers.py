import logging

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from auth_app.models import Organization

logger = logging.getLogger(__name__)


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
        request = self.context.get('request')
        parent = validated_data['parent_id']
        user = request.user
        root_organization: Organization = user.profile.organization
        possible_parent_ids = list(root_organization.children
                                   .values_list('pk', flat=True)
                                   .distinct().order_by()) + [root_organization.top_id]
        if validated_data.get('top_id') != root_organization.top_id:
            raise ValidationError('Укажите в качестве top_id свою ведущую компанию')
        if parent not in possible_parent_ids:
            raise ValidationError('Укажите в качестве parent_id свою ведущую компанию '
                                  'либо один из её департаментов')
        return super().create(validated_data)
