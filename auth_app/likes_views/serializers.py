from django.db import transaction as tr
from rest_framework import serializers
from auth_app.models import Like, LikeKind, LikeStatistics, LikeCommentStatistics
from rest_framework.exceptions import ValidationError
from datetime import datetime


class PressLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['like_kind', 'content_type', 'object_id']

    def create(self, validated_data):

        user = self.context['request'].user
        validated_data['user'] = user
        content_type = validated_data['content_type']
        object_id = validated_data['object_id']
        like_kind = validated_data['like_kind']


