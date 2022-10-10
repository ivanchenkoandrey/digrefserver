from django.db import transaction as tr
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from auth_app.models import Comment, LikeCommentStatistics
from .service import create_comment


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content_type', 'object_id', 'text', 'picture']

    def create(self, validated_data):
        request = self.context.get('request')
        user = self.context['request'].user
        validated_data['user'] = user
        content_type = validated_data['content_type']
        object_id = validated_data['object_id']
        text = validated_data.get('text')
        picture = request.FILES.get('photo')
        validated_data['picture'] = picture
        return create_comment(content_type, object_id, text, picture, user)


class UpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text', 'picture']

    def validate(self, validated_data):

        text = validated_data.get('text')
        request = self.context.get('request')
        picture = request.FILES.get('photo')
        validated_data['picture'] = picture
        if (text is None or text == "") and picture is None:
            raise ValidationError("Не передан параметр text или picture")

        comment = self.instance
        if comment.user_id != self.context['request'].user.id:
            raise ValidationError("Вы не можете изменить комментарий чужого пользователя")

        content_type = comment.content_type
        object_id = comment.object_id
        like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id)
        like_comment_statistics_data = {'last_event_comment': comment}
        super().update(like_comment_statistics, like_comment_statistics_data)
        return validated_data


class DeleteCommentSerializer(serializers.ModelSerializer):

    def validate(self, validated_data):

        comment = self.instance
        if comment.user_id != self.context['request'].user.id:
            raise ValidationError("Вы не можете удалить комментарий чужого пользователя")
        content_type = comment.content_type
        object_id = comment.object_id
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
            last_comment_created = Comment.objects.only('id', 'date_created'). \
                filter(content_type=content_type, object_id=object_id) \
                .order_by('-date_created').first()
            last_comment_modified = Comment.objects.only('id', 'date_last_modified'). \
                filter(content_type=content_type, object_id=object_id) \
                .order_by('-date_last_modified').first()

            like_comment_statistics = LikeCommentStatistics.objects.get(content_type=content_type, object_id=object_id)
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
