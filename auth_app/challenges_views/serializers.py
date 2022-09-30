from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import Challenge


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

        start_balance = validated_data.get('start_balance')
        parameters = validated_data.get('parameters')

        if parameters is None:
            parameters = [{"id": 2, "value": 5},
                          {"id": 1, "value": start_balance // 5, "is_calc": True}]

        elif parameters[0]["id"] == 2:
            parameters.append({"id": 1, "value": start_balance // parameters[0]["value"], "is_calc": True})
        elif parameters[0]["id"] == 1:
            parameters.append({"id": 2, "value": start_balance // parameters[0]["value"], "is_calc": True})
        else:
            raise ValidationError("id в parameters должен принимать значение 1 или 2")
        validated_data['parameters'] = parameters
        print('parameters:', parameters)

        created_challenge_instance = super().create(validated_data)

        return created_challenge_instance

