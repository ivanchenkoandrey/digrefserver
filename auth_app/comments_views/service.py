from utils.crop_photos import crop_image
from utils.fcm_services import get_fcm_tokens_list, get_multiple_users_tokens_list
from utils.handle_image import change_filename
from django.conf import settings
from django.db import transaction as tr
from rest_framework.exceptions import ValidationError
from auth_app.models import Comment, LikeCommentStatistics, Transaction, Challenge, ChallengeReport
from django.contrib.contenttypes.models import ContentType

from utils.notification_services import (get_notification_message_for_thanks_sender_comment,
                                         get_notification_message_for_thanks_recipient_comment,
                                         create_notification, get_extended_pk_list_for_challenge_notifications,
                                         get_notification_message_for_challenge_comment)
from auth_app.tasks import send_multiple_notifications, bulk_create_notifications


def create_comment(content_type, object_id, text, picture, user, transaction, transaction_id, challenge_id,
                   challenge_report_id, comment_id):
    content_type, object_id, model_name = get_object(content_type, object_id, transaction, transaction_id, challenge_id,
                                                     challenge_report_id, comment_id)

    if (text is None or text == "") and picture is None:
        raise ValidationError("Не переданы параметры text или picture")

    with tr.atomic():
        try:
            previous_comment = Comment.objects.get(content_type=content_type, object_id=object_id,
                                                   is_last_comment=True)
        except Comment.DoesNotExist:
            comment_instance = Comment.objects.create(
                content_type=content_type,
                object_id=object_id,
                text=text,
                picture=picture,
                user=user,
                is_last_comment=True,
                previous_comment=None

            )
            content_object = comment_instance.content_object
            if content_object is None:
                raise ValidationError("Объекта с таким id не существует")
            comment = Comment.objects.get(content_type=content_type, object_id=object_id, previous_comment=None)
            try:

                like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type,
                                                                            object_id=object_id)
                like_comment_statistics.first_comment = comment
                like_comment_statistics.last_comment = comment
                like_comment_statistics.last_event_comment = comment
                like_comment_statistics.comment_counter = 1
                like_comment_statistics.save(
                    update_fields=['first_comment', 'last_comment', 'last_event_comment', 'comment_counter'])
            except LikeCommentStatistics.DoesNotExist:

                like_comment_statistics_object = LikeCommentStatistics(content_type=content_type,
                                                                       object_id=object_id,
                                                                       first_comment=comment,
                                                                       last_comment=comment,
                                                                       last_event_comment=comment,
                                                                       comment_counter=1
                                                                       )
                like_comment_statistics_object.save()
            if comment_instance.picture.name is not None:
                comment_instance.picture.name = change_filename(
                    comment_instance.picture.name)
                comment_instance.save(update_fields=['picture'])
                crop_image(comment_instance.picture.name, f"{settings.BASE_DIR}/media/", to_square=False)
            if model_name == 'transaction':
                create_and_send_comment_notifications_for_transactions(comment_instance, object_id, user)
            if model_name == 'challenge':
                create_and_send_comment_notifications_for_challenges(comment_instance, object_id, user)
            return comment_instance.to_json()

        previous_comment.is_last_comment = False
        previous_comment.save(update_fields=['is_last_comment'])

        comment = Comment.objects.create(
            content_type=content_type,
            object_id=object_id,
            text=text,
            picture=picture,
            user=user,
            is_last_comment=True,
            previous_comment=previous_comment
        )

        like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id)
        comment_counter = like_comment_statistics.comment_counter + 1

        like_comment_statistics.last_comment = comment
        like_comment_statistics.last_event_comment = comment
        like_comment_statistics.comment_counter = comment_counter
        like_comment_statistics.save(
            update_fields=['last_comment', 'last_event_comment', 'comment_counter'])

        if model_name == 'transaction':
            create_and_send_comment_notifications_for_transactions(comment, object_id, user)
        if model_name == 'challenge':
            create_and_send_comment_notifications_for_challenges(comment, object_id, user)

        if comment.picture.name is not None:
            comment.picture.name = change_filename(comment.picture.name)
            comment.save(update_fields=['picture'])
            crop_image(comment.picture.name, f"{settings.BASE_DIR}/media/", to_square=False)
        return comment.to_json()


def create_and_send_comment_notifications_for_transactions(comment_instance, object_id, user):
    transaction_instance = (Transaction.objects.select_related('sender', 'recipient')
                            .filter(pk=object_id)
                            .only('sender_id', 'recipient_id', 'id',
                                  'is_anonymous',
                                  'sender__profile__tg_name',
                                  'sender__profile__photo',
                                  'recipient__profile__tg_name',
                                  'recipient__profile__photo').first())
    notification_theme_sender, notification_text_sender = (
        get_notification_message_for_thanks_sender_comment(comment_author=user.profile.tg_name))
    notification_theme_recipient, notification_text_recipient = (
        get_notification_message_for_thanks_recipient_comment(comment_author=user.profile.tg_name))
    notification_data = {
        'comment_from_tg_name': user.profile.tg_name,
        'comment_from_first_name': user.profile.first_name,
        'comment_from_surname': user.profile.surname,
        'comment_from_photo': user.profile.get_thumbnail_photo_url,
        'transaction_id': transaction_instance.id
    }
    push_data = {key: str(value) for key, value in notification_data.items()}
    if user.id != transaction_instance.sender_id:
        create_notification(
            transaction_instance.sender_id,
            comment_instance.pk,
            'C',
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
            comment_instance.pk,
            'C',
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


def create_and_send_comment_notifications_for_challenges(comment, object_id, user):
    challenge, extended_ids_list = get_extended_pk_list_for_challenge_notifications(object_id, user)
    notification_theme, notification_text = (
        get_notification_message_for_challenge_comment(
            comment_author=user.profile.tg_name, challenge_name=challenge.name))
    notification_data = {
        'challenge_id': challenge.pk,
        'challenge_name': challenge.name,
        'comment_from_tg_name': user.profile.tg_name,
        'comment_from_first_name': user.profile.first_name,
        'comment_from_surname': user.profile.surname,
        'comment_from_photo': user.profile.get_thumbnail_photo_url,
    }
    push_data = {key: str(value) for key, value in notification_data.items()}
    tokens_list = get_multiple_users_tokens_list(extended_ids_list)
    bulk_create_notifications.delay(
        extended_ids_list,
        comment.pk,
        'C',
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


def get_object(content_type, object_id, transaction,
               transaction_id, challenge_id, challenge_report_id, comment_id):
    if transaction is not None:
        content_type = ContentType.objects.get_for_model(Transaction)
        object_id = transaction
        model_name = 'transaction'
    elif content_type == "Transaction" or transaction_id is not None:
        content_type = ContentType.objects.get_for_model(Transaction)
        if object_id is None:
            object_id = transaction_id
        model_name = 'transaction'
    elif content_type == 'Challenge' or challenge_id is not None:
        content_type = ContentType.objects.get_for_model(Challenge)
        if object_id is None:
            object_id = challenge_id
        model_name = 'challenge'
    elif content_type == 'ChallengeReport' or challenge_report_id is not None:
        content_type = ContentType.objects.get_for_model(ChallengeReport)
        if object_id is None:
            object_id = challenge_report_id
        model_name = 'challengereport'
    elif content_type == 'Comment' or comment_id is not None:
        content_type = ContentType.objects.get_for_model(Comment)
        if object_id is None:
            object_id = comment_id
        model_name = 'comment'
    else:
        raise ValidationError("Неверно переданы content_type или object_id или не передан один из параметров: "
                              "transaction_id, challenge_id, challenge_report_id, comment_id")
    return content_type, object_id, model_name
