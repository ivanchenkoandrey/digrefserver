from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import Profile, Account, Transaction, TransactionStatus, TransactionClass

User = get_user_model()


class TelegramIDSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    login = serializers.CharField(max_length=20)


class VerifyCodeSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=8)


class ProfileSerializer(serializers.ModelSerializer):
    organization = serializers.CharField(source="organization.name")
    department = serializers.CharField(source="department.name")

    class Meta:
        model = Profile
        exclude = ['user']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ['username', 'profile']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['recipient', 'amount', 'reason']

    def create(self, validated_data):
        sender = self.context['request'].user
        amount = self.validated_data['amount']
        sender_account = Account.objects.filter(
            owner=sender, account_type='D').first()
        current_account_amount = sender_account.amount
        if amount >= current_account_amount:
            raise ValidationError("Перевести можно до 50% имеющейся "
                                  "суммы на счету распределения")
        if amount <= current_account_amount // 2:
            with transaction.atomic():
                sender_account.amount -= amount
                sender_account.save()
                transaction_instance = Transaction.objects.create(
                    sender=self.context['request'].user,
                    recipient=self.validated_data['recipient'],
                    transaction_class='T',
                    amount=self.validated_data['amount'],
                    status='W',
                    reason=self.validated_data['reason']
                )
            return transaction_instance
        else:
            raise ValidationError('Нельзя перевести больше половины '
                                  'имеющейся под распределение суммы')


class TransactionFullSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.profile.tg_name")
    recipient = serializers.CharField(source="recipient.profile.tg_name")
    status = serializers.SerializerMethodField()
    transaction_class = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status_display()

    def get_transaction_class(self, obj):
        return obj.get_transaction_class_display()

    class Meta:
        model = Transaction
        fields = '__all__'
