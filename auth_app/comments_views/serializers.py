from django.db import transaction as tr
from rest_framework import serializers
from auth_app.models import Comment, Transaction, LikeCommentStatistics
from rest_framework.exceptions import ValidationError
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content_type', 'object_id', 'text', 'picture']

    def create(self, validated_data):

        user = self.context['request'].user
        validated_data['user'] = user
        content_type = validated_data['content_type']
        if content_type in ['11', 'transaction']:
            content_type = 11
        elif content_type in ['30', 'challenge']:
            content_type = 30
        elif content_type in ['31', 'challengeReport']:
            content_type = 31

        object_id = validated_data['object_id']
        text = validated_data.get('text')
        image = validated_data.get('picture')

        if (text is None or text == "") and image is None:
            raise ValidationError("Не переданы параметры text или picture")
        with tr.atomic():
            try:
                previous_comment = Comment.objects.get(content_type=content_type, object_id=object_id, is_last_comment=True)
            except Comment.DoesNotExist:
                validated_data['is_last_comment'] = True
                validated_data['previous_comment'] = None

                created_comment_instance = super().create(validated_data)
                comment = Comment.objects.get(content_type=content_type, object_id=object_id, previous_comment=None)
                try:

                    like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id)
                    like_comment_statistics_data = {'first_comment': comment, 'last_comment': comment,
                                                    'last_event_comment': comment,
                                                    'comment_counter': 1}
                    super().update(like_comment_statistics, like_comment_statistics_data)
                except LikeCommentStatistics.DoesNotExist:

                    like_comment_statistics_object = LikeCommentStatistics(content_type=content_type,
                                                                           object_id=object_id,
                                                                           first_comment=comment,
                                                                           last_comment=comment, last_event_comment=comment,
                                                                           comment_counter=1)
                    like_comment_statistics_object.save()
                return created_comment_instance

            data = {'is_last_comment': False}
            super().update(previous_comment, data)
            validated_data['previous_comment'] = previous_comment
            validated_data['is_last_comment'] = True
            created_comment_instance = super().create(validated_data)
            comment = Comment.objects.get(content_type=content_type, object_id=object_id, is_last_comment=True)

            like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id)
            comment_counter = like_comment_statistics.comment_counter + 1
            like_comment_statistics_data = {'last_comment': comment, 'last_event_comment': comment,
                                            'comment_counter': comment_counter}
            super().update(like_comment_statistics, like_comment_statistics_data)
            return created_comment_instance


class UpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text', 'picture']

    def validate(self, validated_data):

        text = validated_data.get('text')
        picture = validated_data.get('picture')
        comment_id = self.instance.id
        if (text is None or text == "") and picture is None:
            raise ValidationError("Не переданы параметры text или picture")

        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            raise ValidationError("Данного комментария не существует")
        if comment.user_id != self.context['request'].user.id:
            raise ValidationError("Вы не можете изменить комментарий чужого пользователя")

        transaction_id = comment.transaction_id
        like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=transaction_id)
        like_comment_statistics_data = {'last_event_comment': comment}
        super().update(like_comment_statistics, like_comment_statistics_data)
        return validated_data


class DeleteCommentSerializer(serializers.ModelSerializer):

    def validate(self, validated_data):
        comment_id = self.instance.id
        validated_data['id'] = comment_id
        try:
            comment = get_object_or_404(Comment, id=comment_id)
        except Comment.DoesNotExist:
            raise ValidationError("Данного комментария не существует")
        if comment.user_id != self.context['request'].user.id:
            raise ValidationError("Вы не можете удалить комментарий чужого пользователя")
        transaction_id = comment.transaction_id
        previous_comment = comment.previous_comment
        with tr.atomic():
            if previous_comment is not None:
                if comment.is_last_comment:
                    data = {"is_last_comment": True}
                    super().update(previous_comment, data)
                try:
                    like_comment_statistics = LikeCommentStatistics.objects.get(last_comment=comment)
                    like_comment_statistics_data = {"last_comment": previous_comment}
                    super().update(like_comment_statistics, like_comment_statistics_data)
                except LikeCommentStatistics.DoesNotExist:
                    pass
                try:
                    next_comment = Comment.objects.get(previous_comment=comment)
                    next_comment_data = {'previous_comment': previous_comment}
                    super().update(next_comment, next_comment_data)

                except Comment.DoesNotExist:
                    pass
            else:
                try:
                    next_comment = Comment.objects.get(previous_comment=comment)
                    next_comment_data = {'previous_comment': None}
                    super().update(next_comment, next_comment_data)
                    try:
                        like_comment_statistics = LikeCommentStatistics.objects.get(first_comment=comment)
                        like_comment_statistics_data = {"first_comment": next_comment}
                        super().update(like_comment_statistics, like_comment_statistics_data)
                    except LikeCommentStatistics.DoesNotExist:
                        pass
                except Comment.DoesNotExist:
                    pass

            # comment.delete()
            last_comment_created = Comment.objects.only('id', 'date_created').filter(transaction_id=transaction_id) \
                .order_by('-date_created').first()
            last_comment_modified = Comment.objects.only('id', 'date_last_modified').filter(transaction_id=transaction_id) \
                .order_by('-date_last_modified').first()

            like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=comment.transaction_id)
            comment_counter = like_comment_statistics.comment_counter - 1
            like_comment_statistics_data = {'comment_counter': comment_counter}
            if last_comment_created is not None:
                if last_comment_modified.date_last_modified != '' and last_comment_modified.date_last_modified is not None:
                    if last_comment_modified.date_last_modified > last_comment_created.date_created:
                        like_comment_statistics_data['last_event_comment'] = last_comment_modified
                    else:
                        like_comment_statistics_data['last_event_comment'] = last_comment_created
                else:
                    like_comment_statistics_data['last_event_comment'] = last_comment_created
            else:
                like_comment_statistics_data['last_event_comment'] = None
            super().update(like_comment_statistics, like_comment_statistics_data)

            return validated_data

    class Meta:
        model = Comment
        fields = '__all__'
