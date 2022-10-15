from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from auth_app.models import Comment, Transaction
from auth_app.serializers import CommentTransactionSerializer
from rest_framework.response import Response
from .serializers import UpdateCommentSerializer, DeleteCommentSerializer
from django.contrib.contenttypes.models import ContentType
from utils.crop_photos import crop_image
from utils.handle_image import change_filename
from django.conf import settings
from .service import create_comment, get_object


class CommentListAPIView(APIView):
    """
    Возвращает список всех комментариев переданной транзакции
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        offset = request.data.get('offset', 0)
        limit = request.data.get('limit', 20)
        include_name = request.data.get('include_name', False)
        is_reverse_order = request.data.get('is_reverse_order', False)
        transaction_id = request.data.get('transaction_id')
        challenge_id = request.data.get('challenge_id')
        challenge_report_id = request.data.get('challenge_report_id')
        content_type, object_id = get_object(content_type, object_id, None, transaction_id, challenge_id,
                                             challenge_report_id, None)
        content_type = content_type.id
        if type(offset) != int or type(limit) != int:
            return Response("offset и limit должны быть типа Int", status=status.HTTP_400_BAD_REQUEST)
        if type(include_name) != bool or type(is_reverse_order) != bool:
            return Response("include_name и is_reverse_order должны быть типа bool", status=status.HTTP_400_BAD_REQUEST)

        context = {"offset": offset, "limit": limit, "include_name": include_name, "is_reverse_order": is_reverse_order}

        if content_type is not None and object_id is not None:
            model_class = ContentType.objects.get_for_id(content_type).model_class()
            try:
                model_object = model_class.objects.get(id=object_id)
                # {"model_class": model_class, "model_object": model_object}
                serializer = CommentTransactionSerializer({"content_type": content_type, "object_id": object_id}, context=context)
                return Response(serializer.data)

            except model_class.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной заданной модели",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр content_type или object_id",
                        status=status.HTTP_400_BAD_REQUEST)


class CreateCommentView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        user = request.user
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        text = request.data.get('text')
        picture = request.FILES.get('photo')
        transaction_id = request.data.get('transaction_id')
        challenge_id = request.data.get('challenge_id')
        challenge_report_id = request.data.get('challenge_report_id')
        comment_id = request.data.get('comment_id')
        transaction = request.data.get('transaction')
        response = create_comment(content_type, object_id, text, picture, user, transaction,
                                  transaction_id, challenge_id, challenge_report_id, comment_id)
        return Response(response)


class UpdateCommentView(UpdateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Comment.objects.all()
    serializer_class = UpdateCommentSerializer
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        pk = instance.id
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            comment = Comment.objects.get(id=pk)
            if comment.picture.name is not None:
                comment.picture.name = change_filename(
                    comment.picture.name)
                comment.save(update_fields=['picture'])
                crop_image(comment.picture.name, f"{settings.BASE_DIR}/media/", to_square=False)
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class DeleteCommentView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Comment.objects.all()
    serializer_class = DeleteCommentSerializer
    lookup_field = 'pk'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_destroy(instance)
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)
