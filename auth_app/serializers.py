import logging
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
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
from utils.crop_photos import crop_image
from utils.current_period import get_current_period
from auth_app.tasks import send_multiple_notifications
from utils.fcm_services import get_fcm_tokens_list
from utils.handle_image import change_filename
from utils.notification_services import (create_notification,
                                         get_notification_message_for_thanks_sender)
from utils.query_debugger import query_debugger
from utils.thumbnail_link import get_thumbnail_link

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
    organization_id = serializers.IntegerField()
    department = serializers.CharField(source="department.name")
    department_id = serializers.IntegerField()
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
        fields = ['transaction_id', 'content_type', 'object_id', 'comments']

    content_type = serializers.SerializerMethodField()
    object_id = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()

    def get_content_type(self, obj):
        model_class = ContentType.objects.get_for_id(obj['content_type'])
        return model_class.name

    def get_object_id(self, obj):
        return obj['object_id']

    def get_transaction_id(self, obj):
        return obj['object_id']

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

        comments_on_transaction = (Comment.objects.filter_by_object(content_type=obj['content_type'],
                                                                    object_id=obj['object_id']).select_related(
            'user__profile')
                                   .only('user__profile__first_name',
                                         'user__profile__photo',
                                         'user__profile__surname',
                                         'text',
                                         'picture',
                                         'date_created',
                                         'date_last_modified').order_by(order_by))
        comments_on_transaction_cut = comments_on_transaction[offset: offset + limit]
        for i in range(len(comments_on_transaction_cut)):

            comment_info = {
                "id": comments_on_transaction_cut[i].id,
                "text": comments_on_transaction_cut[i].text,
                "created": comments_on_transaction_cut[i].date_created,
                "edited": comments_on_transaction_cut[i].date_last_modified
            }
            if getattr(comments_on_transaction_cut[i], "picture"):
                comment_info['picture'] = get_thumbnail_link(comments_on_transaction_cut[i].picture.url)
            else:
                comment_info['picture'] = None

            if include_name:
                avatar = comments_on_transaction_cut[i].user.profile.get_photo_url()
                user_info = {
                    "id": comments_on_transaction_cut[i].user_id,
                    "name": comments_on_transaction_cut[i].user.profile.first_name,
                    "surname": comments_on_transaction_cut[i].user.profile.surname,
                    "avatar": get_thumbnail_link(avatar) if avatar is not None else None
                }

            else:
                user_info = {"id": comments_on_transaction_cut[i].user_id}
            comment_info['user'] = user_info

            comments.append(comment_info)

        return comments


class LikeTransactionSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()
    object_id = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    def get_transaction_id(self, obj):
        return obj['object_id']

    def get_content_type(self, obj):
        model_class = ContentType.objects.get_for_id(obj['content_type'])
        return model_class.name

    def get_object_id(self, obj):
        return obj['object_id']

    @query_debugger
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
            like_kinds = [(like_kind.id, like_kind.code, like_kind.name, like_kind.get_icon_url()) for like_kind in
                          [LikeKind.objects.get(id=like_kind_id)]]

        users_liked = [(like.date_created, like.user, like.like_kind_id)
                       for like in Like.objects.select_related('user__profile', 'like_kind', 'transaction')
                       .only("id", "date_created", 'user__profile__first_name', 'user__profile__photo', 'like_kind',
                             'transaction__id').
                       filter(content_type=obj['content_type'], object_id=obj['object_id'], is_liked=True).order_by(
                '-date_created')]

        for like_kind in like_kinds:
            items = []
            counter = 0
            index = 0
            for i in range(len(users_liked)):

                if users_liked[i][2] == like_kind[0]:
                    if index >= offset and counter < limit:
                        user_info = {"time_of": users_liked[i][0]}
                        if include_name:
                            this_user = {
                                'id': users_liked[i][1].id,
                                'name': users_liked[i][1].profile.first_name,
                                'surname': users_liked[i][1].profile.surname,
                                'avatar': users_liked[i][1].profile.get_photo_url()
                            }

                        else:
                            this_user = {
                                'id': users_liked[i][1].id
                            }
                        user_info['user'] = this_user
                        items.append(user_info)
                        counter += 1
                    index += 1

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
        fields = ['transaction_id', 'content_type', 'object_id', 'likes']


class LikeUserSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    def get_user_id(self, obj):
        return obj.id

    @query_debugger
    def get_likes(self, obj):
        include_code = self.context.get('include_code')
        like_kind_id = self.context.get('like_kind')
        offset = self.context.get('offset')
        limit = self.context.get('limit')

        if include_code:
            like_kinds = [{"id": like_kind.id, "code": like_kind.code, "name": like_kind.name,
                           "icon": like_kind.get_icon_url()} for like_kind in LikeKind.objects.all()]
        else:
            like_kinds = [{"id": like_kind.id, "code": like_kind.code} for like_kind in LikeKind.objects.
            only("id", 'code')]
        likes = {"like_kinds": like_kinds}
        items = []

        if like_kind_id != 'all':
            like_kind = LikeKind.objects.get(id=like_kind_id)

            transactions_liked = [(like.content_type, like.object_id, like.date_created)
                                  for like in Like.objects.filter_by_user_and_like_kind(obj.id, like_kind).
                                  order_by('date_created')]

            transactions_liked_cut = transactions_liked[offset:offset + limit]
            for i in range(len(transactions_liked_cut)):
                model_id = transactions_liked_cut[i][0].name + '_id'
                object_info = {
                    model_id: transactions_liked_cut[i][1],
                    "time_of": transactions_liked_cut[i][2],
                    "like_kind": like_kind_id
                }
                items.append(object_info)
            likes['items'] = items

            if len(transactions_liked_cut) == 0:
                items.append(None)
                likes['items'] = items
            return likes

        else:
            transactions_liked = [(like.content_type, like.object_id, like.date_created, like.like_kind_id)
                                  for like in Like.objects.filter_by_user(obj.id).order_by('-date_created')]
            transactions_liked_cut = transactions_liked[offset: offset + limit]
            for i in range(len(transactions_liked_cut)):
                model_id = transactions_liked_cut[i][0].name + '_id'

                items.append(
                    {
                        model_id: transactions_liked_cut[i][1],
                        "time_of": transactions_liked_cut[i][2],
                        "like_kind": transactions_liked_cut[i][3]
                    }
                )
                likes['items'] = items

            if len(transactions_liked_cut) == 0:
                items = None
                likes['items'] = items
            return likes

    class Meta:
        model = Like
        fields = ['user_id', 'likes']


@query_debugger
class TransactionStatisticsSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField()
    first_comment = serializers.SerializerMethodField()
    last_comment = serializers.SerializerMethodField()
    last_event_comment = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    content_type = serializers.SerializerMethodField()
    object_id = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()

    def get_content_type(self, obj):
        model_class = ContentType.objects.get_for_id(obj['content_type'])
        return model_class.name

    def get_object_id(self, obj):
        return obj['object_id']

    def get_transaction_id(self, obj):
        return obj['object_id']

    def get_comments(self, obj):
        try:
            like_comment_statistics = LikeCommentStatistics.objects.get(content_type=obj['content_type'],
                                                                        object_id=obj['object_id'])
            return like_comment_statistics.comment_counter
        except LikeCommentStatistics.DoesNotExist:
            return 0

    @query_debugger
    def get_comment(self, comment_id, include_name):
        comment = Comment.objects.select_related("user__profile").only("id", "user__profile__first_name",
                                                                       "user__profile__photo", "text", "picture",
                                                                       "date_created", "date_last_modified").get(
            id=comment_id)
        comment_info = {"id": comment_id}
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
        if getattr(comment, "picture"):
            comment_info['picture'] = get_thumbnail_link(comment.picture.url)
        else:
            comment_info['picture'] = None

        comment_info['created'] = comment.date_created
        comment_info['edited'] = comment.date_last_modified
        return comment_info

    @query_debugger
    def get_first_comment(self, obj):
        include_name = self.context.get('include_name')
        include_first_comment = self.context.get('include_first_comment')
        if include_first_comment:
            try:

                likes_comments_statistics = LikeCommentStatistics.objects.select_related("first_comment").only(
                    "first_comment").get(content_type=obj['content_type'], object_id=obj['object_id'])

                first_comment = likes_comments_statistics.first_comment
                if first_comment is not None:
                    return self.get_comment(first_comment.id, include_name)
            except LikeCommentStatistics.DoesNotExist:
                pass
        return None

    def get_last_comment(self, obj):
        include_name = self.context.get('include_name')
        include_last_comment = self.context.get('include_last_comment')
        if include_last_comment:
            try:
                likes_comments_statistics = LikeCommentStatistics.objects.select_related("first_comment").only(
                    "first_comment").get(content_type=obj['content_type'], object_id=obj['object_id'])

                last_comment = likes_comments_statistics.last_comment
                if last_comment is not None:
                    return self.get_comment(last_comment.id, include_name)
            except LikeCommentStatistics.DoesNotExist:
                pass
        return None

    def get_last_event_comment(self, obj):
        include_name = self.context.get('include_name')
        include_last_event_comment = self.context.get('include_last_event_comment')
        if include_last_event_comment:
            try:
                likes_comments_statistics = LikeCommentStatistics.objects.select_related("first_comment").only(
                    "first_comment").get(content_type=obj['content_type'], object_id=obj['object_id'])

                last_event_comment = likes_comments_statistics.last_event_comment
                if last_event_comment is not None:
                    return self.get_comment(last_event_comment.id, include_name)
            except LikeCommentStatistics.DoesNotExist:
                pass
        return None

    @query_debugger
    def get_likes(self, obj):
        include_code = self.context.get('include_code')
        likes = []
        fields = [(like_kind.id, like_kind.code, like_kind.name, like_kind.get_icon_url()) for like_kind in
                  LikeKind.objects.all()]

        try:
            like_statistics = [(statistics.like_kind_id, statistics.like_counter, statistics.last_change_at) for
                               statistics in
                               LikeStatistics.objects.select_related("transaction", "like_kind").only("id",
                                                                                                      "like_counter",
                                                                                                      "like_kind",
                                                                                                      "last_change_at",
                                                                                                      "transaction__id").
                               filter(content_type=obj['content_type'], object_id=obj['object_id'])]
        except LikeStatistics.DoesNotExist:
            pass
        for like_kind in fields:
            like_info = {}
            if include_code:
                like_kind_info = {
                    'id': like_kind[0],
                    'code': like_kind[1],
                    'name': like_kind[2],
                    'icon': like_kind[3]
                }
            else:
                like_kind_info = {
                    'id': like_kind[0],
                    'code': like_kind[1]
                }
            like_info['like_kind'] = like_kind_info
            # default values, if statistics doesn't exist
            like_info['counter'] = 0
            like_info['last_changed'] = None
            for statistics in like_statistics:
                if statistics[0] == like_kind[0]:
                    like_info['counter'] = statistics[1]
                    like_info['last_changed'] = statistics[2]

            likes.append(like_info)

        return likes

    class Meta:
        model = Like
        fields = ['transaction_id', 'content_type', 'object_id', 'comments', 'first_comment', 'last_comment',
                  'last_event_comment', 'likes']


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
        from_income = False
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
        tags = self.make_validations(amount, current_period, reason, recipient, sender, tags)
        sender_distr_account = Account.objects.filter(
            owner=sender, account_type='D', organization_id=None, challenge_id=None).first()
        account_to_save = sender_distr_account
        current_account_amount = sender_distr_account.amount
        if current_account_amount == 0:
            sender_income_account = Account.objects.filter(
                owner=sender, account_type='I', organization_id=None, challenge_id=None).first()
            current_account_amount = sender_income_account.amount
            from_income = True
            account_to_save = sender_income_account
        if current_account_amount - amount < 0:
            logger.info(f"Попытка {sender} перевести сумму больше имеющейся на счету распределения")
            raise ValidationError("Нельзя перевести больше, чем есть на счету")
        if current_account_amount // 2 < amount and current_account_amount > 50:
            logger.info(f"Попытка {sender} перевести сумму, большую либо равную "
                        f"имеющейся сумме на счету распределения")
            raise ValidationError("Перевести можно до 50% имеющейся "
                                  "суммы на счету распределения")
        sender_frozen_account = Account.objects.filter(
            owner=sender, account_type='F', organization_id=None, challenge_id=None).first()
        sender_user_stat = UserStat.objects.get(user=sender, period=current_period)
        with transaction.atomic():
            transaction_instance = Transaction.objects.create(
                sender=self.context['request'].user,
                sender_account=account_to_save,
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
            if not from_income:
                sender_distr_account.amount -= amount
                sender_distr_account.transaction = transaction_instance
                sender_user_stat.distr_thanks += amount
                sender_distr_account.save(update_fields=['amount', 'transaction'])
                sender_user_stat.save(update_fields=['distr_thanks'])
            else:
                sender_income_account.amount -= amount
                sender_income_account.transaction = transaction_instance
                sender_user_stat.income_used_for_thanks += amount
                sender_income_account.save(update_fields=['amount', 'transaction'])
                sender_user_stat.save(update_fields=['income_used_for_thanks'])
            sender_frozen_account.amount += amount
            sender_frozen_account.transaction = transaction_instance
            sender_frozen_account.save(update_fields=['amount', 'transaction'])
            if tags:
                for tag in tags:
                    ObjectTag.objects.create(
                        tag_id=tag,
                        tagged_object=transaction_instance,
                        created_by_id=request.user.pk
                    )
                logger.info(f"{sender} отправил(а) {amount} спасибок на счёт {recipient}")
            if transaction_instance.photo.name is not None:
                transaction_instance.photo.name = change_filename(transaction_instance.photo.name)
                transaction_instance.save(update_fields=['photo'])
                crop_image(transaction_instance.photo.name, f"{settings.BASE_DIR}/media/")
            recipient_tg_name = recipient.profile.tg_name
            status = 'Ожидает'
            notification_sender_theme, notification_sender_text = get_notification_message_for_thanks_sender(
                recipient_tg_name, amount, status
            )
            notification_data = self.get_notification_data(amount, recipient_tg_name, transaction_instance)
            create_notification(
                user_id=sender.pk,
                object_id=transaction_instance.pk,
                _type='T',
                theme=notification_sender_theme,
                text='',
                data=notification_data,
                from_user=sender.pk
            )
            receiver_tokens_list = get_fcm_tokens_list(sender.pk)
            push_data = {key: str(value) for key, value in notification_data.items()}
            send_multiple_notifications.delay(
                title=notification_sender_theme,
                msg=notification_sender_text,
                tokens=receiver_tokens_list,
                data=push_data
            )
            return transaction_instance

    @classmethod
    def get_notification_data(cls, amount, recipient_tg_name, transaction_instance):
        notification_data = {
            "sender_id": transaction_instance.sender_id
            if not transaction_instance.is_anonymous else None,
            "sender_tg_name": transaction_instance.sender.profile.tg_name
            if not transaction_instance.is_anonymous else None,
            "sender_photo": transaction_instance.sender.profile.get_thumbnail_photo_url
            if not transaction_instance.is_anonymous else None,
            "recipient_id": transaction_instance.recipient_id,
            "recipient_tg_name": recipient_tg_name,
            "recipient_photo": transaction_instance.recipient.profile.get_thumbnail_photo_url,
            "status": transaction_instance.status,
            "amount": int(amount),
            "transaction_id": transaction_instance.pk,
            "income_transaction": False
        }
        return notification_data

    @classmethod
    def make_validations(cls, amount, current_period, reason, recipient, sender, tags):
        if amount <= 0:
            logger.info(f"Попытка {sender} перевести сумму меньше либо равную нулю")
            raise ValidationError("Нельзя перевести сумму меньше либо равную нулю")
        if current_period is None:
            logger.info(f"Попытка создать транзакцию, когда закончился период")
            raise ValidationError('Период отправки транзакций закончился')
        if reason is None and tags is None:
            logger.error(f"Не переданы ни своё обоснование, ни ценность")
            raise ValidationError("Нужно либо заполнить поле обоснования, "
                                  "либо указать ID существующего тега (ценности)")
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
                    return list(set(tags_list))
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
        if obj.sender is not None:
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
        if obj.sender_account is not None:
            sender_photo_url = obj.sender_account.owner.profile.get_photo_url()
            sender_data = {
                'sender_id': obj.sender_account.owner.id,
                'sender_tg_name': obj.sender_account.owner.profile.tg_name,
                'sender_first_name': obj.sender_account.owner.profile.first_name,
                'sender_surname': obj.sender_account.owner.profile.surname,
                'sender_photo': get_thumbnail_link(sender_photo_url) if sender_photo_url else None
            }
            if obj.transaction_class == 'H' and obj.to_challenge is not None:
                sender_data.update({"challenge_name": obj.to_challenge.name})
                sender_data.update({"challenge_id": obj.to_challenge.id})
            elif obj.transaction_class in ['W', 'F'] and obj.from_challenge is not None:
                sender_data.update({"challenge_name": obj.from_challenge.name})
                sender_data.update({"challenge_id": obj.from_challenge.id})
            return sender_data

    def get_sender_id(self, obj):
        if obj.sender is not None:
            user_id = self.context.get('user').pk
            if (not obj.is_anonymous
                    or user_id == obj.sender.id):
                return obj.sender.id
        if not obj.is_anonymous and obj.sender_account is not None:
            return obj.sender_account.owner.id

    def get_recipient(self, obj):
        if obj.recipient is not None:
            recipient_photo_url = obj.recipient.profile.get_photo_url()
            return {
                'recipient_id': obj.recipient.id,
                'recipient_tg_name': obj.recipient.profile.tg_name,
                'recipient_first_name': obj.recipient.profile.first_name,
                'recipient_surname': obj.recipient.profile.surname,
                'recipient_photo': get_thumbnail_link(recipient_photo_url) if recipient_photo_url else None
            }
        if obj.recipient_account is not None:
            recipient_photo_url = obj.recipient_account.owner.profile.get_photo_url()
            recipient_data = {
                'recipient_id': obj.recipient_account.owner_id,
                'recipient_tg_name': obj.recipient_account.owner.profile.tg_name,
                'recipient_first_name': obj.recipient_account.owner.profile.first_name,
                'recipient_surname': obj.recipient_account.owner.profile.surname,
                'recipient_photo': get_thumbnail_link(recipient_photo_url) if recipient_photo_url else None
            }
            if obj.transaction_class == 'W' and obj.from_challenge is not None:
                recipient_data.update({'challenge_name': obj.from_challenge.name})
            return recipient_data

    def get_recipient_id(self, obj):
        if obj.recipient is not None:
            return obj.recipient.id
        if obj.recipient_account is not None:
            return obj.recipient_account.owner_id

    def get_can_user_cancel(self, obj):
        if obj.sender is not None:
            user_id = self.context.get('user').pk
            return (obj.status in ['W', 'G', 'A']
                    and user_id == obj.sender.id
                    and (datetime.now(timezone.utc) - obj.created_at).seconds < settings.GRACE_PERIOD)
        return False

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
