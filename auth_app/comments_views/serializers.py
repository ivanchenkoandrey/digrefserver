from rest_framework import serializers
from auth_app.models import Comment, Transaction, LikeCommentStatistics
from rest_framework.exceptions import ValidationError
from datetime import datetime
from django.shortcuts import get_object_or_404


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['transaction', 'text', 'picture']

    def create(self, validated_data):
        transaction = validated_data['transaction']

        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['date_created'] = datetime.now()
        content = validated_data['text']
        image = validated_data['picture']

        if (content is None or content == "") and image is None:
            raise ValidationError("Не переданы параметры text или picture")

        try:
            previous_comment = Comment.objects.get(transaction_id=transaction.id, is_last_comment=True)
        except Comment.DoesNotExist:

            validated_data['is_last_comment'] = True
            validated_data['previous_comment'] = None

            created_comment_instance = super().create(validated_data)
            comment = Comment.objects.get(transaction_id=transaction.id, previous_comment=None)
            try:

                like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=transaction.id)
                like_comment_statistics_data = {'first_comment': comment, 'last_comment': comment,
                                                'last_event_comment': comment,
                                                'last_like_or_comment_change_at': datetime.now(), 'comment_counter': 1}
                super().update(like_comment_statistics, like_comment_statistics_data)
            except LikeCommentStatistics.DoesNotExist:

                like_comment_statistics_object = LikeCommentStatistics(transaction_id=transaction.id,
                                                                       first_comment=comment,
                                                                       last_comment=comment, last_event_comment=comment,
                                                                       last_like_or_comment_change_at=datetime.now(),
                                                                       comment_counter=1)
                like_comment_statistics_object.save()
            return created_comment_instance

        data = {'is_last_comment': False}
        super().update(previous_comment, data)
        validated_data['previous_comment'] = previous_comment
        validated_data['is_last_comment'] = True
        created_comment_instance = super().create(validated_data)
        comment = Comment.objects.get(transaction_id=transaction.id, is_last_comment=True)

        like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=transaction.id)
        comment_counter = like_comment_statistics.comment_counter + 1
        like_comment_statistics_data = {'last_comment': comment, 'last_event_comment': comment,
                                        'last_like_or_comment_change_at': datetime.now(),
                                        'comment_counter': comment_counter}
        super().update(like_comment_statistics, like_comment_statistics_data)
        return created_comment_instance


class UpdateCommentSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(required=True)

    class Meta:
        model = Comment
        fields = ['id', 'text', 'picture']

    def create(self, validated_data):

        text = validated_data['text']
        picture = validated_data['picture']
        comment_id = validated_data['id']
        if (text is None or text == "") and picture is None:
            raise ValidationError("Не переданы параметры text или picture")

        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            raise ValidationError("Данного комментария не существует")

        data = {'date_last_modified': datetime.now()}
        if picture is not None:
            data['picture'] = picture

        if text is not None and text != "":
            data['text'] = text

        transaction = comment.transaction
        like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=transaction.id)
        like_comment_statistics_data = {'last_event_comment': comment,
                                        'last_like_or_comment_change_at': datetime.now()}
        super().update(like_comment_statistics, like_comment_statistics_data)
        return super().update(comment, data)


class DeleteCommentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)

    class Meta:
        model = Comment
        fields = ['id']

    def create(self, validated_data):
        comment_id = validated_data['id']
        try:
            comment = get_object_or_404(Comment, id=comment_id)
        except Comment.DoesNotExist:
            raise ValidationError("Данного комментария не существует")
        transaction_id = comment.transaction_id
        previous_comment = comment.previous_comment
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

        comment.delete()
        last_comment_created = Comment.objects.all().filter(transaction_id=transaction_id) \
            .order_by('-date_created').first()
        last_comment_modified = Comment.objects.all().filter(transaction_id=transaction_id) \
            .order_by('-date_last_modified').first()

        like_comment_statistics = LikeCommentStatistics.objects.get(transaction_id=comment.transaction_id)
        comment_counter = like_comment_statistics.comment_counter - 1
        like_comment_statistics_data = {'last_like_or_comment_change_at': datetime.now(),
                                        'comment_counter': comment_counter}
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

        # TODO
        transaction = Transaction.objects.get(id=transaction_id)
        data = {"is_commentable": True}
        return super().update(transaction, data)
