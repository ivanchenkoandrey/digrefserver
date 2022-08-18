from rest_framework import serializers


class EmployeeSerializer(serializers.Serializer):
    tg_name = serializers.CharField()
    tg_id = serializers.CharField()
    organization_id = serializers.IntegerField()
    department_id = serializers.IntegerField()
    photo = serializers.ImageField(required=False)
    surname = serializers.CharField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField(required=False)
    nickname = serializers.CharField(required=False)
    hired_at = serializers.DateField(required=False)
    fired_at = serializers.DateField(required=False)
