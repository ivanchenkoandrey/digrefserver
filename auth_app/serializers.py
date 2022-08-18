import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import Profile, Account, Transaction, UserStat, Period, Contact
from utils.current_period import get_current_period

User = get_user_model()

logger = logging.getLogger(__name__)


class FindUserSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    login = serializers.CharField(max_length=50)


class VerifyCodeSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=8)


class SearchUserSerializer(serializers.Serializer):
    data = serializers.CharField(max_length=50)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['contact_type', 'contact_id']


class ProfileSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, required=False)
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


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class TransactionPartialSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False)

    class Meta:
        model = Transaction
        fields = ['recipient', 'amount', 'reason', 'photo']

    def create(self, validated_data):
        sender = self.context['request'].user
        recipient = self.validated_data['recipient']
        photo = self.context['request'].FILES.get('photo')
        if recipient.accounts.filter(account_type__in=['S', 'T']).exists():
            raise ValidationError('Нельзя отправлять спасибки на системный аккаунт')
        amount = self.validated_data['amount']
        if amount <= 0:
            logger.info(f"Попытка {sender} перевести сумму меньше либо равную нулю")
            raise ValidationError("Нельзя перевести сумму меньше либо равную нулю")
        sender_distr_account = Account.objects.filter(
            owner=sender, account_type='D').first()
        current_account_amount = sender_distr_account.amount
        if amount >= current_account_amount:
            logger.info(f"Попытка {sender} перевести сумму, большую либо равную "
                        f"имеющейся сумме на счету распределения")
            raise ValidationError("Перевести можно до 50% имеющейся "
                                  "суммы на счету распределения")
        sender_frozen_account = Account.objects.filter(
            owner=sender, account_type='F').first()
        sender_user_stat = UserStat.objects.get(user=sender, period=get_current_period())
        if amount <= current_account_amount // 2:
            with transaction.atomic():
                sender_distr_account.amount -= amount
                sender_frozen_account.amount += amount
                sender_user_stat.distr_thanks += amount
                sender_distr_account.save(update_fields=['amount'])
                sender_frozen_account.save(update_fields=['amount'])
                sender_user_stat.save(update_fields=['distr_thanks'])
                transaction_instance = Transaction.objects.create(
                    sender=self.context['request'].user,
                    recipient=recipient,
                    transaction_class='T',
                    amount=self.validated_data['amount'],
                    status='W',
                    reason=self.validated_data['reason'],
                    is_public=False,
                    is_anonymous=False,
                    photo=photo
                )
                logger.info(f"{sender} отправил(а) {amount} спасибок на счёт {recipient}")
            return transaction_instance
        else:
            logger.info(f"Попытка {sender} перевести сумму, "
                        f"меньшую чем полная сумма на счету распределения, "
                        f"но большую чем её половина")
            raise ValidationError('Нельзя перевести больше половины '
                                  'имеющейся под распределение суммы')


class TransactionFullSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    sender_id = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    recipient_id = serializers.SerializerMethodField()
    transaction_status = serializers.SerializerMethodField()
    transaction_class = serializers.SerializerMethodField()
    expire_to_cancel = serializers.DateTimeField()

    def get_transaction_status(self, obj):
        return {
            'id': obj.status,
            'name': obj.get_status_display()
        }

    def get_transaction_class(self, obj):
        return {
            'id': obj.transaction_class,
            'name': obj.get_transaction_class_display()
        }

    def get_sender(self, obj):
        return {
            'sender_id': obj.sender.id,
            'sender_tg_name': obj.sender.profile.tg_name,
            'sender_first_name': obj.sender.profile.first_name,
            'sender_surname': obj.sender.profile.surname
        }

    def get_sender_id(self, obj):
        return obj.sender.id

    def get_recipient(self, obj):
        return {
            'recipient_id': obj.recipient.id,
            'recipient_tg_name': obj.recipient.profile. tg_name,
            'recipient_first_name': obj.recipient.profile.first_name,
            'recipient_surname': obj.recipient.profile.surname
        }

    def get_recipient_id(self, obj):
        return obj.recipient.id

    class Meta:
        model = Transaction
        exclude = ['status']


class TransactionCancelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['status']


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = '__all__'
