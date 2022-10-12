import logging
from datetime import datetime
from django.db import transaction as tr
from rest_framework.exceptions import ValidationError
from auth_app.models import Like, LikeKind, LikeStatistics, LikeCommentStatistics, Transaction, ChallengeReport, \
                            Challenge, Comment
from django.contrib.contenttypes.models import ContentType
from auth_app.comments_views.service import get_object

logger = logging.getLogger(__name__)


def press_like(user, content_type, object_id, like_kind, transaction,
               transaction_id, challenge_id, challenge_report_id, comment_id):
    like_kinds = LikeKind.objects.all()
    like_kind = LikeKind.objects.get(id=like_kind)

    content_type, object_id = get_object(content_type, object_id, transaction, transaction_id, challenge_id,
                                         challenge_report_id, comment_id)
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
            another_like_statistics.like_counter = another_like_statistics.like_counter - 1
            another_like_statistics.last_change_at = datetime.now()
            another_like_statistics.save(update_fields=['like_counter', 'last_change_at'])

            like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                         like_kind=like_kind)
            like_statistics.like_counter = like_statistics.like_counter + 1
            like_statistics.last_change_at = datetime.now()
            like_statistics.save(update_fields=['like_counter', 'last_change_at'])

            like = Like(
                        user=user,
                        content_type=content_type,
                        object_id=object_id,
                        like_kind=like_kind,
                        is_liked=True,
                        date_deleted=None
                        )
            like.save()
            return like.to_json()

        else:
            existing_like_same_type_liked = Like.objects.filter(content_type=content_type, object_id=object_id,
                                                                user=user, is_liked=True, like_kind=like_kind).first()
            if existing_like_same_type_liked is not None:

                like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                             like_kind=like_kind)
                like_statistics.like_counter = like_statistics.like_counter - 1
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

                like = Like(content_type=content_type, object_id=object_id, user=user, is_liked=True,
                            like_kind=like_kind)
                content_object = like.content_object
                if content_object is None:
                    raise ValidationError("Объекта с таким id не существует")
                else:
                    like.save()
                return like.to_json()
