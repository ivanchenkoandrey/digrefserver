from rest_framework import serializers
from auth_app.models import Challenge, Organization
from rest_framework.exceptions import ValidationError


class CreateChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = ['name', 'description', 'end_at', 'start_balance', 'parameters', 'photo']

    def create(self, validated_data):
        creator = self.context['request'].user
        validated_data['creator'] = creator
        validated_data['organized_by'] = creator
        validated_data['states'] = ['P']
        validated_data['challenge_mode'] = ['P']

        name = validated_data.get('name')
        description = validated_data.get('description')
        end_at = validated_data.get('end_at')
        start_balance = validated_data.get('start_balance')
        parameters = validated_data.get('parameters')

        if parameters is None:
            arr = [{"id": 2, "value": 5},
                   {"id": 1, "value": start_balance // 5}]
        elif parameters.get("id") == 2:
            arr = [{"id": 2, "value": parameters.get("value")},
                   {"id": 1, "value": start_balance // parameters.get("value")}]
        elif parameters.get("id") == 1:
            arr = [{"id": 1, "value": parameters.get("value")},
                   {"id": 2, "value": start_balance // parameters.get("value")}]
        else:
            raise ValidationError("id в parameters должен принимать значение 1 или 2")
        print('parameters:', arr)

        if name is None or name == "":
            raise ValidationError("Не передан параметр name ")

        created_challenge_instance = super().create(validated_data)

        return created_challenge_instance

