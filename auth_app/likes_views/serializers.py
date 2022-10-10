from django.db import transaction as tr
from rest_framework import serializers
from auth_app.models import Like, LikeKind, LikeStatistics, LikeCommentStatistics
from rest_framework.exceptions import ValidationError
from datetime import datetime


class PressLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['like_kind', 'content_type', 'object_id']

    def create(self, validated_data):

        user = self.context['request'].user
        validated_data['user'] = user
        content_type = validated_data['content_type']
        object_id = validated_data['object_id']
        like_kind = validated_data['like_kind']

        like_kinds = LikeKind.objects.all()

        like_statistics_data = {}
        with tr.atomic():
            try:
                like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id, like_kind_id=like_kind.id)
                like_statistics_data['last_change_at'] = datetime.now()
                super().update(like_statistics, like_statistics_data)

            except LikeStatistics.DoesNotExist:
                like_statistics_object = LikeStatistics(content_type=content_type, object_id=object_id, like_kind=like_kind,
                                                        last_change_at=datetime.now(), like_counter=0)
                like_statistics_object.save()

            try:
                like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id,)
                like_comments_statistics_data = {'last_like_or_comment_change_at': datetime.now()}
                super().update(like_comment_statistics, like_comments_statistics_data)
            except LikeCommentStatistics.DoesNotExist:
                like_comment_statistics_object = LikeCommentStatistics(content_type=content_type, object_id=object_id,
                                                                       last_like_or_comment_change_at=datetime.now())
                like_comment_statistics_object.save()

            if content_type is None or object_id is None:
                raise ValidationError("Не передан content_type или object_id")

            if like_kind.id == like_kinds[0].id:
                another_like_kind = like_kinds[1]
            else:
                another_like_kind = like_kinds[0]

            try:
                stat = LikeStatistics.objects.get(content_type=content_type, object_id=object_id, like_kind_id=another_like_kind)
            except LikeStatistics.DoesNotExist:
                another_like_kind_statistics_object = LikeStatistics(content_type=content_type, object_id=object_id, like_kind=another_like_kind,
                                                                     like_counter=0)
                another_like_kind_statistics_object.save()

            existing_like_different_like_type = Like.objects.filter(content_type=content_type, object_id=object_id,
                                                                    user=user, is_liked=True,
                                                                    like_kind_id=another_like_kind.id).first()

            if existing_like_different_like_type is not None:

                validated_data['is_liked'] = False
                validated_data['like_kind'] = existing_like_different_like_type.like_kind
                validated_data['date_deleted'] = datetime.now()
                super().update(existing_like_different_like_type, validated_data)

                # update statistics for prev like_type from which like is retrieved
                another_like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id,
                                                                     like_kind_id=another_like_kind.id)
                another_like_statistics_data = {'like_counter': another_like_statistics.like_counter - 1,
                                                'last_change_at': datetime.now()}
                super().update(another_like_statistics, another_like_statistics_data)

                validated_data['is_liked'] = True
                validated_data['like_kind'] = like_kind
                validated_data['date_deleted'] = None

                like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id, like_kind_id=like_kind.id)
                like_statistics_data['like_counter'] = like_statistics.like_counter + 1
                like_statistics_data['last_change_at'] = datetime.now()
                super().update(like_statistics, like_statistics_data)
                return super().create(validated_data)

            else:
                existing_like_same_type_liked = Like.objects.filter(content_type=content_type, object_id=object_id,
                                                                    user=user, is_liked=True, like_kind=like_kind).first()
                if existing_like_same_type_liked is not None:
                    validated_data['is_liked'] = False
                    validated_data['like_kind'] = like_kind
                    validated_data['date_deleted'] = datetime.now()

                    like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id, like_kind_id=like_kind.id)
                    like_statistics_data['like_counter'] = like_statistics.like_counter - 1
                    like_statistics_data['last_change_at'] = datetime.now()
                    super().update(like_statistics, like_statistics_data)

                    return super().update(existing_like_same_type_liked, validated_data)
                else:

                    validated_data['is_liked'] = True
                    validated_data['like_kind'] = like_kind
                    like_statistics = LikeStatistics.objects.get(content_type=content_type, object_id=object_id, like_kind_id=like_kind.id)
                    like_statistics_data['like_counter'] = like_statistics.like_counter + 1
                    like_statistics_data['last_change_at'] = datetime.now()
                    super().update(like_statistics, like_statistics_data)

                    like = Like(content_type=content_type, object_id=object_id, user=user, is_liked=True, like_kind=like_kind)
                    content_object = like.content_object
                    if content_object is None:
                        raise ValidationError("Объекта с таким id не существует")
                    else:
                        like.save()
                    return validated_data
