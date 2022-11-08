import logging
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.db import transaction as tr
from rest_framework.exceptions import ValidationError

from auth_app.comments_views.service import get_object
from auth_app.models import Like, LikeKind, LikeStatistics, LikeCommentStatistics, Transaction, Comment
from auth_app.tasks import send_multiple_notifications, bulk_create_notifications
from utils.fcm_services import get_fcm_tokens_list, get_multiple_users_tokens_list
from utils.notification_services import (get_notification_message_for_thanks_sender_reaction,
                                         get_notification_message_for_thanks_recipient_reaction,
                                         get_notification_message_for_challenge_reaction,
                                         get_notification_message_for_comment_author_reaction,
                                         create_notification, get_extended_pk_list_for_challenge_notifications)

logger = logging.getLogger(__name__)


def press_like(user, content_type, object_id, like_kind, transaction,
               transaction_id, challenge_id, challenge_report_id, comment_id):
    like_kinds = LikeKind.objects.all()
    like_kind = LikeKind.objects.get(id=like_kind)

    content_type, object_id, model_name = get_object(content_type, object_id, transaction,
                                                     transaction_id, challenge_id, challenge_report_id, comment_id)
    with tr.atomic():
        try:
            like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                         like_kind=like_kind)
            like_statistics.last_change_at = datetime.now()
            like_statistics.save(update_fields=['last_change_at'])

        except LikeStatistics.DoesNotExist:
            like_statistics_object = LikeStatistics(content_type=content_type, object_id=object_id, like_kind=like_kind,
                                                    last_change_at=datetime.now(), like_counter=0)
            like_statistics_object.save()

        try:
            like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type,
                                                                        object_id=object_id)
            like_comment_statistics.last_like_or_comment_change_at = datetime.now()
            like_comment_statistics.save(update_fields=['last_like_or_comment_change_at'])

        except LikeCommentStatistics.DoesNotExist:
            like_comment_statistics_object = LikeCommentStatistics(content_type=content_type, object_id=object_id,
                                                                   last_like_or_comment_change_at=datetime.now())
            like_comment_statistics_object.save()

        if transaction is None and (content_type is None or object_id is None):
            raise ValidationError("Не передан content_type или object_id или transaction_id")

        if like_kind.id == like_kinds[0].id:
            another_like_kind = like_kinds[1]
        else:
            another_like_kind = like_kinds[0]
        try:
            stat = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                              like_kind_id=another_like_kind.id)
        except LikeStatistics.DoesNotExist:
            another_like_kind_statistics_object = LikeStatistics(content_type=content_type, object_id=object_id,
                                                                 like_kind=another_like_kind,
                                                                 like_counter=0)
            another_like_kind_statistics_object.save()

        existing_like_different_like_type = Like.objects.filter(content_type=content_type, object_id=object_id,
                                                                user=user, is_liked=True,
                                                                like_kind_id=another_like_kind.id).first()
        if existing_like_different_like_type is not None:
            existing_like_different_like_type.is_liked = False
            existing_like_different_like_type.date_deleted = datetime.now()
            existing_like_different_like_type.save(update_fields=['is_liked', 'date_deleted'])

            # update statistics for prev like_type from which like is retrieved
            another_like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                                 like_kind_id=another_like_kind)
            another_like_statistics.like_counter -= 1
            another_like_statistics.last_change_at = datetime.now()
            another_like_statistics.save(update_fields=['like_counter', 'last_change_at'])

            like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                         like_kind=like_kind)
            like_statistics.like_counter += 1
            like_statistics.last_change_at = datetime.now()
            like_statistics.save(update_fields=['like_counter', 'last_change_at'])

            like = Like.objects.create(
                user=user,
                content_type=content_type,
                object_id=object_id,
                like_kind=like_kind,
                is_liked=True,
                date_deleted=None
            )
            return like.to_json()
        else:
            existing_like_same_type_liked = Like.objects.filter(content_type=content_type, object_id=object_id,
                                                                user=user, is_liked=True, like_kind=like_kind).first()
            if existing_like_same_type_liked is not None:

                like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                             like_kind=like_kind)
                like_statistics.like_counter -= 1
                like_statistics.last_change_at = datetime.now()
                like_statistics.save(update_fields=['like_counter', 'last_change_at'])

                existing_like_same_type_liked.is_liked = False
                existing_like_same_type_liked.date_deleted = datetime.now()
                existing_like_same_type_liked.save(update_fields=['is_liked', 'date_deleted'])
                return existing_like_same_type_liked.to_json()
            else:
                like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                             like_kind=like_kind)
                like_statistics.like_counter += 1
                like_statistics.last_change_at = datetime.now()
                like_statistics.save(update_fields=['like_counter', 'last_change_at'])

                like = Like.objects.create(content_type=content_type, object_id=object_id, user=user, is_liked=True,
                                           like_kind=like_kind)
                content_object = like.content_object
                if content_object is None:
                    raise ValidationError("Объекта с таким id не существует")
                if model_name == 'transaction':
                    create_and_send_transaction_reactions_notifications(like, object_id, user)
                if model_name == 'challenge':
                    create_and_send_challenge_reactions_notifications(like, object_id, user)
                if model_name == 'comment':
                    create_and_send_comment_reactions_notifications(like, object_id, user)
                return like.to_json()


def create_and_send_comment_reactions_notifications(like, object_id, user):
    comment = Comment.objects.select_related('user__profile').filter(pk=object_id).only(
        'user__profile__first_name',
        'user__profile__surname',
        'user__profile__photo',
        'user__profile__tg_name',
        'user_id',
        'id'
    ).first()
    comment_content_type = ContentType.objects.get_for_id(comment.content_type_id)
    notification_data = {
        "comment_author_id": comment.user_id,
        "comment_author_tg_name": comment.user.profile.tg_name,
        "comment_author_first_name": comment.user.profile.first_name,
        "comment_author_surname": comment.user.profile.surname,
        "comment_author_photo": comment.get_thumbnail_photo_url,
        "comment_content_type": comment_content_type.model,
        "comment_object_id": comment.object_id
    }
    push_data = {key: str(value) for key, value in notification_data.items()}
    notification_theme, notification_text = (
        get_notification_message_for_comment_author_reaction(reaction_sender=user.profile.tg_name))
    if user.id != comment.user_id:
        create_notification(
            comment.user_id,
            like.pk,
            'L',
            notification_theme,
            notification_text,
            data=notification_data
        )
        send_multiple_notifications.delay(
            notification_theme,
            notification_text,
            get_fcm_tokens_list(comment.user_id),
            data=push_data
        )


def create_and_send_challenge_reactions_notifications(like, object_id, user):
    challenge, extended_ids_list = get_extended_pk_list_for_challenge_notifications(object_id, user)
    notification_theme, notification_text = (
        get_notification_message_for_challenge_reaction(
            reaction_sender=user.profile.tg_name, challenge_name=challenge.name))
    notification_data = {
        'challenge_id': challenge.pk,
        'challenge_name': challenge.name,
        'reaction_from_tg_name': user.profile.tg_name,
        'reaction_from_first_name': user.profile.first_name,
        'reaction_from_surname': user.profile.surname,
        'reaction_from_photo': user.profile.get_thumbnail_photo_url,
    }
    push_data = {key: str(value) for key, value in notification_data.items()}
    tokens_list = get_multiple_users_tokens_list(extended_ids_list)
    bulk_create_notifications.delay(
        extended_ids_list,
        like.pk,
        'L',
        notification_theme,
        notification_text,
        data=notification_data,
        from_user=challenge.creator_id
    )
    send_multiple_notifications.delay(
        notification_theme,
        notification_text,
        tokens_list,
        push_data
    )


def create_and_send_transaction_reactions_notifications(like, object_id, user):
    transaction_instance = (Transaction.objects.select_related('sender', 'recipient')
                            .filter(pk=object_id)
                            .only('sender_id', 'recipient_id', 'id',
                                  'is_anonymous',
                                  'sender__profile__tg_name',
                                  'sender__profile__photo',
                                  'recipient__profile__tg_name',
                                  'recipient__profile__photo').first())
    notification_theme_sender, notification_text_sender = (
        get_notification_message_for_thanks_sender_reaction(reaction_sender=user.profile.tg_name))
    notification_theme_recipient, notification_text_recipient = (
        get_notification_message_for_thanks_recipient_reaction(reaction_sender=user.profile.tg_name))
    notification_data = {
        'like_from_tg_name': user.profile.tg_name,
        'like_from_first_name': user.profile.first_name,
        'like_from_surname': user.profile.surname,
        'like_from_photo': user.profile.get_thumbnail_photo_url,
        'transaction_id': transaction_instance.id
    }
    push_data = {key: str(value) for key, value in notification_data.items()}
    if user.id != transaction_instance.sender_id:
        create_notification(
            transaction_instance.sender_id,
            like.pk,
            'L',
            notification_theme_sender,
            notification_text_sender,
            data=notification_data,
            from_user=transaction_instance.sender_id
        )
        send_multiple_notifications.delay(
            notification_theme_sender,
            notification_text_sender,
            get_fcm_tokens_list(transaction_instance.sender_id),
            data=push_data
        )
    if user.id != transaction_instance.recipient_id:
        create_notification(
            transaction_instance.recipient_id,
            like.pk,
            'L',
            notification_theme_recipient,
            notification_text_recipient,
            data=notification_data,
            from_user=transaction_instance.sender_id
        )
        send_multiple_notifications.delay(
            notification_theme_sender,
            notification_text_sender,
            get_fcm_tokens_list(transaction_instance.recipient_id),
            data=push_data
        )
