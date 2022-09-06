from rest_framework import serializers

from auth_app.models import Tag, Reason


class ReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reason
        fields = ['id', 'data']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'pict']

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return {key: result[key] for key in result if result[key] is not None}


class TagRetrieveSerializer(serializers.ModelSerializer):
    reasons = ReasonSerializer(many=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'pict', 'reasons']

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return {key: result[key] for key in result if result[key] is not None}
