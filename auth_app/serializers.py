import logging
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from auth_app.models import (Profile, Account, Transaction,
                             UserStat, Period, Contact,
                             UserRole, Tag, ObjectTag,
                             Comment, Like, LikeKind,
                             LikeStatistics,
                             LikeCommentStatistics)
from utils.current_period import get_current_period
from utils.thumbnail_link import get_thumbnail_link
from utils.crop_photos import crop_image
from utils.handle_image import change_transaction_filename

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
    photo = serializers.SerializerMethodField()

    def get_photo(self, obj):
        if obj.photo:
            return get_thumbnail_link(obj.photo.url)

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


class CommentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['transaction_id', 'comments']

    transaction_id = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    def get_transaction_id(self, obj):
        return obj.id

    def get_comments(self, obj):
        offset = self.context.get('offset')
        limit = self.context.get('limit')
        include_name = self.context.get('include_name')
        is_reverse_order = self.context.get('is_reverse_order')
        if is_reverse_order:
            order_by = "-date_created"
        else:
            order_by = "date_created"
        comments = []
        counter = 0
        comments_on_transaction = Comment.objects.filter_by_transaction(obj.id).order_by(order_by)
        for i in range(len(comments_on_transaction)):
            if i >= offset - 1 and counter < limit:
                comment_info = {
                    "id": comments_on_transaction[i].id,

                    "text": comments_on_transaction[i].text,
                    "picture": comments_on_transaction[i].picture,
                    "created": comments_on_transaction[i].date_created,
                    "edited": comments_on_transaction[i].date_last_modified
                }
                if comments_on_transaction[i].picture:
                    comment_info['picture'] = comments_on_transaction[i].picture
                else:
                    comment_info['picture'] = None
                if include_name:
                    user_info = {
                        "id": comments_on_transaction[i].user_id,
                        "name": comments_on_transaction[i].user.profile.first_name,
                        "avatar": comments_on_transaction[i].user.profile.get_photo_url()
                    }

                else:
                    user_info = {"id": comments_on_transaction[i].user_id}
                comment_info['user'] = user_info

                comments.append(comment_info)
                counter += 1

        return comments


class LikeTransactionSerializer(serializers.ModelSerializer):

    transaction_id = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    def get_transaction_id(self, obj):
        return obj.id

    def get_likes(self, obj):
        include_code = self.context.get('include_code')
        include_name = self.context.get('include_name')
        like_kind_id = self.context.get('like_kind')
        offset = self.context.get('offset')
        limit = self.context.get('limit')
        likes = []
        if like_kind_id == "all":
            like_kinds = [(like_kind.id, like_kind.code, like_kind.name, like_kind.get_icon_url()) for like_kind in
                          LikeKind.objects.all()]
        else:
            like_kinds = [(like_kind.id, like_kind.name, like_kind.get_icon_url()) for like_kind in
                          [LikeKind.objects.get(id=like_kind_id)]]
        # {"user_id": 1}

        for like_kind in like_kinds:
            items = []
            users_liked = [(like.date_created, like.user)
                           for like in Like.objects.filter_by_transaction_and_like_kind(obj.id, like_kind[0]).order_by('date_created')]

            counter = 0
            for i in range(len(users_liked)):
                if i >= offset and counter < limit:
                    user_info = {"time_of": users_liked[i][0]}
                    if include_name:
                        this_user = {
                                'id': users_liked[i][1].id,
                                'name': users_liked[i][1].profile.first_name,
                                'avatar': users_liked[i][1].profile.get_photo_url()
                            }

                    else:
                        this_user = {
                            'id': users_liked[i][1].id
                        }
                    user_info['user'] = this_user
                    items.append(user_info)
                    counter += 1

            if include_code:
                likes.append(
                    {
                        "like_kind": {
                            'id': like_kind[0],
                            'code': like_kind[1],
                            'name': like_kind[2],
                            'icon': like_kind[3],
                        },
                        "items": items
                    }

                )
            else:
                likes.append(
                    {
                        "like_kind": {
                            'id': like_kind[0],
                            'code': like_kind[1],
                        },
                        "items": items
                    }

                )

        return likes

    class Meta:
        model = Like
        fields = ['transaction_id', 'likes']


class LikeUserSerializer(serializers.ModelSerializer):

    likes = serializers.SerializerMethodField()

    user_id = serializers.SerializerMethodField()

    def get_user_id(self, obj):
        return obj.id

    def get_likes(self, obj):
        include_code = self.context.get('include_code')
        like_kind_id = self.context.get('like_kind')
        offset = self.context.get('offset')
        limit = self.context.get('limit')
        likes = {}
        if include_code:
            like_kinds = [{"id": like_kind.id, "code": like_kind.code, "name": like_kind.name,
                           "icon": like_kind.get_icon_url()} for like_kind in LikeKind.objects.all()]
        else:
            like_kinds = [{"id": like_kind.id, "code": like_kind.code} for like_kind in LikeKind.objects.all()]
        likes["like_kinds"] = like_kinds
        # {"user_id": 1}
        if like_kind_id != 'all':
            like_kind = LikeKind.objects.get(id=like_kind_id)
            items = []
            transactions_liked = [(like.transaction_id, like.date_created)
                                  for like in Like.objects.filter_by_user_and_like_kind(obj.id, like_kind).order_by('date_created')]
            counter = 0
            for i in range(len(transactions_liked)):
                if i >= offset - 1 and counter < limit:
                    items.append(
                        {
                            "transaction_id": transactions_liked[i][0],
                            "time_of": transactions_liked[i][1],
                            "like_kind": like_kind_id,
                        }
                    )
                    likes['items'] = items
                    counter += 1
            if len(transactions_liked) == 0:
                items.append(None)
                likes['items'] = items
            return likes

        else:

            items = []
            transactions_liked = [(like.transaction_id, like.date_created, like.like_kind_id)
                                  for like in Like.objects.filter_by_user(obj.id).order_by('date_created')]
            counter = 0
            for i in range(len(transactions_liked)):
                if i >= offset and counter < limit:
                    items.append(
                        {
                            "transaction_id": transactions_liked[i][0],
                            "time_of": transactions_liked[i][1],
                            "like_kind": transactions_liked[i][2],
                        }
                    )
                    likes['items'] = items
                    counter += 1
            if len(transactions_liked) == 0:
                items = None
                likes['items'] = items
            return likes

    class Meta:
        model = Like
        fields = ['user_id', 'likes']


class TransactionStatisticsSerializer(serializers.ModelSerializer):

    transaction_id = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    first_comment = serializers.SerializerMethodField()
    last_comment = serializers.SerializerMethodField()
    last_event_comment = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    def get_transaction_id(self, obj):
        return obj.id

    def get_comments(self, obj):
        try:
            like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=obj.id)
            return like_comment_statistics.comment_counter
        except LikeCommentStatistics.DoesNotExist:
            return 0

    def get_comment(self, comment, include_name):

        comment_info = {"id": comment.id}
        if include_name:
            user = {
                    "id": comment.user.id,
                    "name": comment.user.profile.first_name,
                    "avatar": comment.user.profile.get_photo_url()
            }
        else:
            user = {"id": comment.user.id}
        comment_info['user'] = user
        comment_info['text'] = comment.text
        if comment.picture:
            comment_info['picture'] = comment.picture
        else:
            comment_info['picture'] = None
        comment_info['created'] = comment.date_created
        comment_info['edited'] = comment.date_last_modified
        return comment_info

    def get_first_comment(self, obj):
        include_name = self.context.get('include_name')
        include_first_comment = self.context.get('include_first_comment')
        if include_first_comment:
            try:
                likes_comments_statistics = LikeCommentStatistics.objects.get(transaction_id=obj.id)
                first_comment = likes_comments_statistics.first_comment
                if first_comment is not None:
                    return self.get_comment(first_comment, include_name)
            except LikeCommentStatistics.DoesNotExist:
                pass
        return None

    def get_last_comment(self, obj):
        include_name = self.context.get('include_name')
        include_last_comment = self.context.get('include_last_comment')
        if include_last_comment:
            try:
                likes_comments_statistics = LikeCommentStatistics.objects.get(transaction_id=obj.id)
                last_comment = likes_comments_statistics.last_comment
                if last_comment is not None:
                    return self.get_comment(last_comment, include_name)
            except LikeCommentStatistics.DoesNotExist:
                pass
        return None

    def get_last_event_comment(self, obj):
        include_name = self.context.get('include_name')
        include_last_event_comment = self.context.get('include_last_event_comment')
        if include_last_event_comment:
            try:
                likes_comments_statistics = LikeCommentStatistics.objects.get(transaction_id=obj.id)
                last_event_comment = likes_comments_statistics.last_event_comment
                if last_event_comment is not None:
                    return self.get_comment(last_event_comment, include_name)
            except LikeCommentStatistics.DoesNotExist:
                pass
        return None

    def get_likes(self, obj):
        include_code = self.context.get('include_code')
        likes = []
        # {"transaction_id":6}
        fields = [(like_kind.id, like_kind.code, like_kind.name, like_kind.get_icon_url()) for like_kind in LikeKind.objects.all()]

        if include_code:
            for like_kind in fields:
                like_info = {
                    'like_kind': {
                                'id': like_kind[0],
                                'code': like_kind[1],
                                'name': like_kind[2],
                                'icon': like_kind[3]
                                }
                }
                try:
                    like_statistics = LikeStatistics.objects.get(transaction_id=obj.id, like_kind=like_kind[0])
                    like_info['counter'] = like_statistics.like_counter
                    like_info['last_changed'] = like_statistics.last_change_at
                except LikeStatistics.DoesNotExist:
                    like_info['counter'] = 0
                    like_info['last_changed'] = None
                likes.append(like_info)
            return likes
        else:
            for like_kind in fields:
                like_info = {
                    'like_kind': {
                        'id': like_kind[0],
                        'code': like_kind[1]
                    }
                }
                try:
                    like_statistics = LikeStatistics.objects.get(transaction_id=obj.id, like_kind=like_kind[0])
                    like_info['counter'] = like_statistics.like_counter
                    like_info['last_changed'] = like_statistics.last_change_at
                except LikeStatistics.DoesNotExist:
                    like_info['counter'] = 0
                    like_info['last_changed'] = None

                likes.append(like_info)
            return likes

    class Meta:
        model = Like
        fields = ['transaction_id', 'comments', 'first_comment', 'last_comment', 'last_event_comment', 'likes']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class TransactionPartialSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False)
    tags = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Transaction
        fields = ['recipient', 'amount',
                  'photo', 'is_anonymous',
                  'reason', 'reason_def', 'tags']

    def get_tags(self, obj):
        try:
            tags = self.context.get('request').data.get('tags')
            if tags is not None:
                tags = [int(tag) for tag in tags.split()]
            else:
                tags = []
            return tags
        except ValueError:
            pass

    def create(self, validated_data):
        current_period = get_current_period()
        request = self.context.get('request')
        tags = request.data.get('tags')
        sender = self.context['request'].user
        recipient = self.validated_data['recipient']
        photo = request.FILES.get('photo')
        reason = self.data.get('reason')
        reason_def = self.data.get('reason_def')
        amount = self.validated_data['amount']
        is_anonymous = self.validated_data['is_anonymous']
        tags = self.make_validations(amount, current_period, reason, reason_def, recipient, sender, tags)
        sender_distr_account = Account.objects.filter(
            owner=sender, account_type='D').first()
        current_account_amount = sender_distr_account.amount
        if current_account_amount - amount < 0:
            logger.info(f"Попытка {sender} перевести сумму больше имеющейся на счету распределения")
            raise ValidationError("Нельзя перевести больше, чем есть на счету")
        if current_account_amount // 2 < amount and current_account_amount > 50:
            logger.info(f"Попытка {sender} перевести сумму, большую либо равную "
                        f"имеющейся сумме на счету распределения")
            raise ValidationError("Перевести можно до 50% имеющейся "
                                  "суммы на счету распределения")
        sender_frozen_account = Account.objects.filter(
            owner=sender, account_type='F').first()
        sender_user_stat = UserStat.objects.get(user=sender, period=current_period)
        with transaction.atomic():
            transaction_instance = Transaction.objects.create(
                sender=self.context['request'].user,
                recipient=recipient,
                transaction_class='T',
                amount=self.validated_data['amount'],
                status='G',
                reason=reason,
                is_public=True,
                is_anonymous=is_anonymous,
                period=current_period,
                photo=photo,
                reason_def_id=reason_def
            )
            sender_distr_account.amount -= amount
            sender_distr_account.transaction = transaction_instance
            sender_frozen_account.amount += amount
            sender_frozen_account.transaction = transaction_instance
            sender_user_stat.distr_thanks += amount
            sender_distr_account.save(update_fields=['amount', 'transaction'])
            sender_frozen_account.save(update_fields=['amount', 'transaction'])
            sender_user_stat.save(update_fields=['distr_thanks'])
            if tags:
                for tag in tags:
                    ObjectTag.objects.create(
                        tag_id=tag,
                        tagged_object=transaction_instance,
                        created_by_id=request.user.pk
                    )
                logger.info(f"{sender} отправил(а) {amount} спасибок на счёт {recipient}")
            if transaction_instance.photo is not None:
                transaction_instance.photo.name = change_transaction_filename(transaction_instance.photo.name)
                transaction_instance.save(update_fields=['photo'])
                crop_image(transaction_instance.photo.name, f"{settings.BASE_DIR}/media/")
            return transaction_instance

    @classmethod
    def make_validations(cls, amount, current_period, reason, reason_def, recipient, sender, tags):
        if amount <= 0:
            logger.info(f"Попытка {sender} перевести сумму меньше либо равную нулю")
            raise ValidationError("Нельзя перевести сумму меньше либо равную нулю")
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
            if not isinstance(tags, str):
                logger.info(f"Попытка передать ценности не строкой")
                raise ValidationError('Передайте ценности (теги) для данного объекта строкой')
            else:
                try:
                    tags_list = list(map(int, tags.split()))
                    possible_tag_ids = set(Tag.objects.values_list('id', flat=True))
                    for tag in tags_list:
                        if tag not in possible_tag_ids:
                            logger.info(f"Ценность (тег) с ID {tag} не найдена")
                            raise ValidationError(f'Ценность (тег) с ID {tag} не найдена')
                    return tags_list
                except ValueError:
                    raise ValidationError(f'Передайте строку в виде "1 2 3"')


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
    photo = serializers.SerializerMethodField()

    def get_photo(self, obj):
        if obj.photo:
            return get_thumbnail_link(obj.photo.url)

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
        sender_photo_url = obj.sender.profile.get_photo_url()
        if (not obj.is_anonymous
                or user_id == obj.sender.id):
            return {
                'sender_id': obj.sender.id,
                'sender_tg_name': obj.sender.profile.tg_name,
                'sender_first_name': obj.sender.profile.first_name,
                'sender_surname': obj.sender.profile.surname,
                'sender_photo': get_thumbnail_link(sender_photo_url) if sender_photo_url else None
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
        recipient_photo_url = obj.recipient.profile.get_photo_url()
        return {
            'recipient_id': obj.recipient.id,
            'recipient_tg_name': obj.recipient.profile. tg_name,
            'recipient_first_name': obj.recipient.profile.first_name,
            'recipient_surname': obj.recipient.profile.surname,
            'recipient_photo': get_thumbnail_link(recipient_photo_url) if recipient_photo_url else None
        }

    def get_recipient_id(self, obj):
        return obj.recipient.id

    def get_can_user_cancel(self, obj):
        user_id = self.context.get('user').pk
        return (obj.status in ['W', 'G', 'A']
                and user_id == obj.sender.id
                and (datetime.now(timezone.utc) - obj.created_at).seconds < settings.GRACE_PERIOD)

    def get_tags(self, obj):
        return obj._objecttags.values('tag_id', name=F('tag__name'))

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
