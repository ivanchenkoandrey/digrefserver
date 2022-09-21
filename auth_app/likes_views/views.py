import logging
from rest_framework.permissions import IsAuthenticated
from auth_app.models import Like, Transaction, User, LikeKind
from auth_app.serializers import LikeTransactionSerializer, LikeUserSerializer
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, status
from .serializers import PressLikeSerializer

logger = logging.getLogger(__name__)


class LikesTransactionListAPIView(APIView):

    """
    Список всех лайков переданной транзакции
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        transaction_id = request.data.get('transaction_id')
        like_kind = request.data.get('like_kind')
        include_code = request.data.get('include_code')
        include_name = request.data.get('include_name')
        offset = request.data.get('offset')
        limit = request.data.get('limit')

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

        if transaction_id is not None:
            try:
                transaction = Transaction.objects.get(id=transaction_id)
                serializer = LikeTransactionSerializer([transaction], many=True, context=context)

                return Response(serializer.data[0])

            except Transaction.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной транзакции",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр transaction_id",
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
        include_code = request.data.get('include_code')
        offset = request.data.get('offset')
        limit = request.data.get('limit')

        if offset is None:
            offset = 0
        if limit is None:
            limit = 20
        if include_code is None:
            include_code = False

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
                users = [user]
                serializer = LikeUserSerializer(users, many=True, context=context)
                return Response(serializer.data[0])

            except User.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одному пользователю",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр user_id",
                        status=status.HTTP_400_BAD_REQUEST)


class PressLikeView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Like.objects.all()
    serializer_class = PressLikeSerializer




