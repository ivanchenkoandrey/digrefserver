import logging

from django.db.models import Max
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
