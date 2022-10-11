from utils.crop_photos import crop_image
from utils.handle_image import change_filename
from django.conf import settings
from django.db import transaction as tr
from rest_framework.exceptions import ValidationError
from auth_app.models import Comment, LikeCommentStatistics, Transaction, Challenge, ChallengeReport
from django.contrib.contenttypes.models import ContentType


def create_comment(content_type, object_id, text, picture, user, transaction_id):
    if content_type in ['Transaction', 'transaction']:
        content_type = ContentType.objects.get_for_model(Transaction)
    elif content_type in ['Challenge', 'challenge']:
        content_type = ContentType.objects.get_for_model(Challenge)
    elif content_type in ['ChallengeReport', 'challengeReport', 'challengereport']:
        content_type = ContentType.objects.get_for_model(ChallengeReport)
    elif content_type in ['Comment', 'comment']:
        content_type = ContentType.objects.get_for_model(Comment)
    if content_type is None:
        content_type = ContentType.objects.get_for_model(Transaction)
        object_id = transaction_id

    if (text is None or text == "") and picture is None:
        raise ValidationError("Не переданы параметры text или picture")
    with tr.atomic():
        try:
            previous_comment = Comment.objects.get(content_type=content_type, object_id=object_id,
                                                   is_last_comment=True)
        except Comment.DoesNotExist:
            comment_instance = Comment(
                content_type=content_type,
                object_id=object_id,
                text=text,
                picture=picture,
                user=user,
                is_last_comment=True,
                previous_comment=None

            )
            comment_instance.save()
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
                like_comment_statistics.save(update_fields=['first_comment', 'last_comment', 'last_event_comment', 'comment_counter'])
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
            return comment_instance.to_json()

        previous_comment.is_last_comment = False
        previous_comment.save(update_fields=['is_last_comment'])

        comment = Comment(
            content_type=content_type,
            object_id=object_id,
            text=text,
            picture=picture,
            user=user,
            is_last_comment=True,
            previous_comment=previous_comment
        )
        comment.save()

        like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id)
        comment_counter = like_comment_statistics.comment_counter + 1

        like_comment_statistics.last_comment = comment
        like_comment_statistics.last_event_comment = comment
        like_comment_statistics.comment_counter = comment_counter
        like_comment_statistics.save(
            update_fields=['last_comment', 'last_event_comment', 'comment_counter'])

        if comment.picture.name is not None:
            comment.picture.name = change_filename(
                comment.picture.name)
            comment.save(update_fields=['picture'])
            crop_image(comment.picture.name, f"{settings.BASE_DIR}/media/", to_square=False)
        return comment.to_json()
