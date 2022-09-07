import logging
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import (Profile, Account, Transaction,
                             UserStat, Period, Contact,
                             UserRole, Tag, ObjectTag)
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
        fields = ['id', 'contact_type', 'contact_id']


class ProfileSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, required=False)
    organization = serializers.CharField(source="organization.name")
    department = serializers.CharField(source="department.name")
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = Profile
        exclude = ['user']


class ProfileAdminSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, required=False)
    organization_id = serializers.SerializerMethodField()
    organization = serializers.CharField(source="organization.name")
    department_id = serializers.SerializerMethodField()
    department = serializers.CharField(source="department.name")

    def get_organization_id(self, obj):
        return obj.organization_id

    def get_department_id(self, obj):
        return obj.department_id

    class Meta:
        model = Profile
        exclude = ['user']


class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = UserRole
        fields = ['role_name', 'department_name']

    def get_role_name(self, obj):
        return obj.get_role_display()

    def get_department_name(self, obj):
        if obj.organization is not None:
            return obj.organization.name
        return None


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    privileged = UserRoleSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ['username', 'profile', 'privileged']


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
    tags_list = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Transaction
        fields = ['recipient', 'amount',
                  'photo', 'is_anonymous',
                  'reason', 'reason_def', 'tags_list']

    def get_tags_list(self, obj):
        return self.context.get('request').data.get('tags_list')

    def create(self, validated_data):
        current_period = get_current_period()
        request = self.context.get('request')
        tags_list = request.data.get('tags_list')
        sender = self.context['request'].user
        recipient = self.validated_data['recipient']
        photo = request.FILES.get('photo')
        reason = self.data.get('reason')
        reason_def = self.data.get('reason_def')
        if reason is not None and reason_def is not None:
            reason = None
        amount = self.validated_data['amount']
        is_anonymous = self.validated_data['is_anonymous']
        self.make_validations(amount, current_period, reason, reason_def, recipient, sender, tags_list)
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
        sender_user_stat = UserStat.objects.get(user=sender, period=current_period)
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
                    reason=reason,
                    is_public=True,
                    is_anonymous=is_anonymous,
                    period=current_period,
                    photo=photo,
                    reason_def_id=reason_def
                )
                if tags_list:
                    for tag in tags_list:
                        ObjectTag.objects.create(
                            tag_id=tag,
                            tagged_object=transaction_instance,
                            created_by_id=request.user.pk
                        )

                logger.info(f"{sender} отправил(а) {amount} спасибок на счёт {recipient}")
            return transaction_instance
        else:
            logger.info(f"Попытка {sender} перевести сумму, "
                        f"меньшую чем полная сумма на счету распределения, "
                        f"но большую чем её половина")
            raise ValidationError('Нельзя перевести больше половины '
                                  'имеющейся под распределение суммы')

    @classmethod
    def make_validations(cls, amount, current_period, reason, reason_def, recipient, sender, tags):
        if current_period is None:
            logger.info(f"Попытка создать транзакцию, когда закончился период")
            raise ValidationError('Период отправки транзакций закончился')
        if reason is None and reason_def is None:
            logger.error(f"Не переданы ни своё обоснование, ни готовое обоснование")
            raise ValidationError("Нужно либо заполнить поле обоснования, "
                                  "либо указать ID уже существующего обоснования (благодарности)")
        if recipient.accounts.filter(account_type__in=['S', 'T']).exists():
            logger.info(f"Попытка отправить спасибки на системный аккаунт")
            raise ValidationError('Нельзя отправлять спасибки на системный аккаунт')
        if tags is not None:
            if not isinstance(tags, list):
                logger.info(f"Попытка передать ценности не списком")
                raise ValidationError('Передайте ценности (теги) для данного объекта списком')
            else:
                possible_tag_ids = set(Tag.objects.values_list('id', flat=True))
                for tag in tags:
                    if tag not in possible_tag_ids:
                        logger.info(f"Ценность (тег) с ID {tag} не найдена")
                        raise ValidationError(f'Ценность (тег) с ID {tag}не найдена')
        if amount <= 0:
            logger.info(f"Попытка {sender} перевести сумму меньше либо равную нулю")
            raise ValidationError("Нельзя перевести сумму меньше либо равную нулю")


class TransactionFullSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    sender_id = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    recipient_id = serializers.SerializerMethodField()
    transaction_status = serializers.SerializerMethodField()
    transaction_class = serializers.SerializerMethodField()
    expire_to_cancel = serializers.DateTimeField()
    can_user_cancel = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    reason_def = serializers.SerializerMethodField()

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
        user_id = self.context.get('user').pk
        if (not obj.is_anonymous
                or user_id == obj.sender.id):
            return {
                'sender_id': obj.sender.id,
                'sender_tg_name': obj.sender.profile.tg_name,
                'sender_first_name': obj.sender.profile.first_name,
                'sender_surname': obj.sender.profile.surname,
                'sender_photo': obj.sender.profile.get_photo_url()
            }
        return {
            'sender_id': None,
            'sender_tg_name': 'anonymous',
            'sender_first_name': None,
            'sender_surname': None,
            'sender_photo': None
        }

    def get_sender_id(self, obj):
        user_id = self.context.get('user').pk
        if (not obj.is_anonymous
                or user_id == obj.sender.id):
            return obj.sender.id
        return None

    def get_recipient(self, obj):
        return {
            'recipient_id': obj.recipient.id,
            'recipient_tg_name': obj.recipient.profile. tg_name,
            'recipient_first_name': obj.recipient.profile.first_name,
            'recipient_surname': obj.recipient.profile.surname,
            'recipient_photo': obj.recipient.profile.get_photo_url()
        }

    def get_recipient_id(self, obj):
        return obj.recipient.id

    def get_can_user_cancel(self, obj):
        user_id = self.context.get('user').pk
        return (obj.status in ['W', 'G', 'A']
                and user_id == obj.sender.id
                and (datetime.now(timezone.utc) - obj.created_at).seconds < settings.GRACE_PERIOD)

    def get_tags(self, obj):
        return obj.tags.values('tag__id', 'tag__name')

    def get_reason_def(self, obj):
        if obj.reason_def is not None:
            return obj.reason_def.data

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


class ContactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['contact_id']

    def validate(self, attrs):
        contact_type = self.instance.contact_type
        contact_id = attrs.get('contact_id')
        if contact_type and contact_id:
            if '@' not in contact_id and contact_type == '@':
                raise ValidationError('В адресе электронной почты должен быть символ @')
        return attrs
