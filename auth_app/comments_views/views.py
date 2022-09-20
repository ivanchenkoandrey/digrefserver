from rest_framework import authentication, status
from rest_framework.generics import CreateAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from auth_app.models import Comment, Transaction
from auth_app.serializers import CommentTransactionSerializer
from rest_framework.response import Response
from .serializers import CreateCommentSerializer, UpdateCommentSerializer, DeleteCommentSerializer


class CommentListAPIView(APIView):
    """
    Возвращает список всех комментариев переданной транзакции
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        transaction_id = request.data.get('transaction_id')
        offset = request.data.get('offset')
        limit = request.data.get('limit')
        include_name = request.data.get('include_name')
        is_reverse_order = request.data.get('is_reverse_order')

        if offset is None:
            offset = 0
        if limit is None:
            limit = 20

        if include_name is None:
            include_name = False

        # return Response("Параметр include_name передан неверно. Введите true или false",
        #                         status=status.HTTP_400_BAD_REQUEST)

        if is_reverse_order is None:
            is_reverse_order = False

        # return Response("Параметр is_reverse_order передан неверно. Введите True или False",
        #                         status=status.HTTP_400_BAD_REQUEST)
        context = {"offset": offset, "limit": limit, "include_name": include_name, "is_reverse_order": is_reverse_order}

        if transaction_id is not None:
            try:
                # transaction = Organization.objects.get(pk=organization_id)
                transaction = Transaction.objects.get(id=transaction_id)
                serializer = CommentTransactionSerializer([transaction], many=True, context=context)

                return Response(serializer.data)

            except Transaction.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной транзакции",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр transaction_id",
                        status=status.HTTP_400_BAD_REQUEST)


class CreateCommentView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Comment.objects.all()
    serializer_class = CreateCommentSerializer


class UpdateCommentView(UpdateAPIView):
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    queryset = Comment.objects.all()
    serializer_class = UpdateCommentSerializer
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
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
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)
