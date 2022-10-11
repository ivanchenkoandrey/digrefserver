import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework import authentication, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Transaction, User, LikeKind, Challenge, ChallengeReport, Comment
from auth_app.serializers import LikeTransactionSerializer, LikeUserSerializer
from .service import press_like

logger = logging.getLogger(__name__)


class LikesListAPIView(APIView):

    """
    Список всех лайков переданной модели
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        like_kind = request.data.get('like_kind')
        include_code = request.data.get('include_code')
        include_name = request.data.get('include_name')
        transaction_id = request.data.get('transaction_id')
        offset = request.data.get('offset')
        limit = request.data.get('limit')
        if content_type in ['Transaction', 'transaction']:
            content_type = ContentType.objects.get_for_model(Transaction).id
        elif content_type in ['Challenge', 'challenge']:
            content_type = ContentType.objects.get_for_model(Challenge).id
        elif content_type in ['ChallengeReport', 'challengeReport', 'challengereport']:
            content_type = ContentType.objects.get_for_model(ChallengeReport).id
        elif content_type in ['Comment', 'comment']:
            content_type = ContentType.objects.get_for_model(Comment).id

        if content_type is None:
            content_type = ContentType.objects.get_for_model(Transaction).id
            object_id = transaction_id

        if offset is None:
            offset = 0
        if limit is None:
            limit = 20
        if include_code is None:
            include_code = False
        if include_name is None:
            include_name = False

        if type(offset) != int or type(limit) != int:
            return Response("offset и limit должны быть типа Int", status=status.HTTP_400_BAD_REQUEST)
        if type(include_name) != bool or type(include_code) != bool:
            return Response("include_name и include_code должны быть типа bool", status=status.HTTP_400_BAD_REQUEST)

        if like_kind is None:
            like_kind = "all"
        else:
            try:
                likekind = LikeKind.objects.get(id=like_kind)
            except LikeKind.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одному типу лайка",
                                status=status.HTTP_404_NOT_FOUND)

        context = {"include_code": include_code, "like_kind": like_kind, "include_name": include_name,
                   "offset": offset, "limit": limit}

        if object_id is not None and content_type is not None:
            model_class = ContentType.objects.get_for_id(content_type).model_class()
            try:
                model_object = model_class.objects.get(id=object_id)
                serializer = LikeTransactionSerializer({"content_type": content_type, "object_id": object_id}, context=context)
                return Response(serializer.data)

            except model_class.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной заданной модели",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр object_id или content_type",
                        status=status.HTTP_400_BAD_REQUEST)


class LikesUserListAPIView(APIView):

    """
    Список всех лайков переданного пользователя
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):

        # user_id = request.user.id  # get the user_id from session
        # TODO
        # optionally other users with higher privilege can get access to other users' likes
        # need to check for the privilege (admin, coordinator, ..)
        user_id = request.data.get('user_id')
        like_kind = request.data.get('like_kind')
        include_code = request.data.get('include_code', False)
        offset = request.data.get('offset', 0)
        limit = request.data.get('limit', 20)

        if type(offset) != int or type(limit) != int:
            return Response("offset и limit должны быть типа Int", status=status.HTTP_400_BAD_REQUEST)
        if type(include_code) != bool:
            return Response("include_name и include_code должны быть типа bool", status=status.HTTP_400_BAD_REQUEST)

        if like_kind is None:
            like_kind = "all"
        else:
            try:
                likekind = LikeKind.objects.get(id=like_kind)
            except LikeKind.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одному типу лайка",
                                status=status.HTTP_404_NOT_FOUND)

        context = {"include_code": include_code, "like_kind": like_kind, "offset": offset, "limit": limit}

        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
                serializer = LikeUserSerializer(user, context=context)
                return Response(serializer.data)

            except User.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одному пользователю",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр user_id",
                        status=status.HTTP_400_BAD_REQUEST)


class PressLikeView(APIView):
    """
        Нажатие лайка
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        user = request.user
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        like_kind = request.data.get('like_kind')
        transaction = request.data.get('transaction')
        response = press_like(user, content_type, object_id, like_kind, transaction)
        return Response(response)




