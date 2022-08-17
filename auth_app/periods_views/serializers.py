import datetime

from rest_framework import serializers
from auth_app.models import Period
from rest_framework.exceptions import ValidationError


class PeriodSerializer(serializers.ModelSerializer):

    class Meta:
        model = Period
        fields = '__all__'

    def validate(self, attrs):
        today = datetime.date.today()
        if attrs['start_date'] >= attrs['end_date']:
            raise ValidationError('Дата начала периода должна быть позже даты окончания!')
        elif attrs['start_date'] < today:
            raise ValidationError('Дата начала периода не может быть в прошлом!')
        elif attrs['end_date'] < today:
            raise ValidationError('Дата окончания периода не может быть в прошлом!')
        return attrs
