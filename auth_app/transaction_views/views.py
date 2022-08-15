import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Transaction, Period
from auth_app.serializers import (TransactionPartialSerializer,
                                  TransactionFullSerializer, TransactionCancelSerializer)
from auth_app.service import (update_transactions_by_controller,
                              is_controller_data_is_valid,
                              cancel_transaction_by_user, is_cancel_transaction_request_is_valid)
from utils.custom_permissions import IsController

logger = logging.getLogger(__name__)


class SendCoinView(CreateModelMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    queryset = Transaction.objects.all()
    serializer_class = TransactionPartialSerializer

    def post(self, request, *args, **kwargs):
        logger.info(f"Пользователь {request.user} отправил "
                    f"следующие данные для совершения транзакции: {request.data}")
        return self.create(request, *args, **kwargs)


class CancelTransactionByUserView(UpdateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionCancelSerializer
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    def update(self, request, *args, **kwargs):
        if not is_cancel_transaction_request_is_valid(request.data):
            logger.info(f'Неправильный запрос на отмену транзакции: {request.data}')
            return Response(status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"Пользователь {request.user} отправил "
                    f"следующие данные для отмены транзакции: {request.data}")
        instance: Transaction = self.get_object()
        if instance.status == 'D':
            logger.info(f"Попытка отмены транзакции с id {instance.pk} пользователем {request.user}")
            return Response(f"Транзакция уже отменена", status=status.HTTP_400_BAD_REQUEST)
        timedelta = timezone.now() - instance.created_at
        if timedelta.seconds > settings.GRACE_PERIOD:
            logger.info(f"Попытка отменить транзакцию с id {instance.pk} пользователем {request.user} "
                        f"по истечении grace периода (превышение {timedelta.seconds - settings.GRACE_PERIOD} секунд)")
            return Response(f"Время возможности отмены транзакции истекло", status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            cancel_transaction_by_user(instance, request, serializer)
            return Response(serializer.data)


class VerifyOrCancelTransactionByControllerView(APIView):
    permission_classes = [IsController]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def get(cls, request, *args, **kwargs):
        queryset = Transaction.objects.filter_to_use_by_controller().order_by('-created_at')
        serializer = TransactionFullSerializer(queryset, many=True)
        logger.info(f"Контроллер {request.user} смотрит список транзакций для подтверждения / отклонения")
        return Response(serializer.data)

    @classmethod
    def put(cls, request, *args, **kwargs):
        data = request.data
        if is_controller_data_is_valid(data):
            response = update_transactions_by_controller(data, request)
            logger.info(f"Контроллер {request.user} выполнил подтверждение / отклонение транзакций")
            return Response(response)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class TransactionsByUserView(ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    serializer_class = TransactionFullSerializer

    def get(self, request, *args, **kwargs):
        logger.info(f"Пользователь {self.request.user} смотрит список транзакций")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Transaction.objects.filter_by_user(self.request.user).order_by('-updated_at')


class SingleTransactionByUserView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    serializer_class = TransactionFullSerializer

    def get(self, request, *args, **kwargs):
        _transaction = self.get_object()
        logger.info(f"Пользователь {self.request.user} смотрит "
                    f"транзакцию c id {_transaction.pk}")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Transaction.objects.filter_by_user(self.request.user)


@api_view(http_method_names=['GET'])
@authentication_classes([authentication.SessionAuthentication,
                         authentication.TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_transaction_list_by_period(request, period_id):
    period = get_object_or_404(Period, pk=period_id)
    transactions_queryset = Transaction.objects.filter_by_period(request.user, period)
    serializer = TransactionFullSerializer(transactions_queryset, many=True)
    return Response(serializer.data)