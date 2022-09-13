import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, authentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Transaction, Period
from auth_app.serializers import (TransactionPartialSerializer, TransactionFullSerializer,
                                  TransactionCancelSerializer, TransactionStatisticsSerializer)
from auth_app.service import (update_transactions_by_controller,
                              is_controller_data_is_valid,
                              cancel_transaction_by_user, is_cancel_transaction_request_is_valid,
                              AlreadyUpdatedByControllerError, NotWaitingTransactionError)
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context


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
        if instance.sender != request.user:
            logger.info(f"Попытка отмены транзакции с id {instance.pk} пользователем {request.user}")
            raise ValidationError(f"Пользователь может отменить только свою транзакцию")
        if instance.status not in ['W', 'G', 'A']:
            logger.info(f"Попытка отмены транзакции с id {instance.pk} пользователем {request.user}")
            raise ValidationError(f"Пользователь может отменить только ожидающую транзакцию")
        timedelta = timezone.now() - instance.created_at
        if timedelta.seconds > settings.GRACE_PERIOD:
            logger.info(f"Попытка отменить транзакцию с id {instance.pk} пользователем {request.user} "
                        f"по истечении grace периода (превышение {timedelta.seconds - settings.GRACE_PERIOD} секунд)")
            raise ValidationError(f"Время возможности отмены транзакции истекло")
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
        serializer = TransactionFullSerializer(queryset, many=True, context={'user': request.user})
        logger.info(f"Контроллер {request.user} смотрит список транзакций для подтверждения / отклонения")
        return Response(serializer.data)

    @classmethod
    def put(cls, request, *args, **kwargs):
        data = request.data
        try:
            if is_controller_data_is_valid(data):
                response = update_transactions_by_controller(data, request)
                logger.info(f"Контроллер {request.user} выполнил подтверждение / отклонение транзакций")
                return Response(response)
        except AlreadyUpdatedByControllerError:
            return Response("ID транзакций должны быть различными!",
                            status=status.HTTP_400_BAD_REQUEST)
        except NotWaitingTransactionError:
            return Response("В запросе присутствует ID транзакции, которую не следует подтверждать!",
                            status=status.HTTP_400_BAD_REQUEST)
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user': self.request.user})
        return context


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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user': self.request.user})
        return context


class TransactionStatisticsAPIView(APIView):

    """
    Статистика комментариев и лайков указанной транзакции
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]

    @classmethod
    def post(cls, request, *args, **kwargs):
        transaction_id = request.data.get('transaction_id')
        include_code = request.data.get('include_code')
        include_name = request.data.get('include_name')
        include_first_comment = request.data.get('include_first_comment')
        include_last_comment = request.data.get('include_last_comment')
        include_last_event_comment = request.data.get('include_last_event_comment')

        if include_name is None:
            include_name = False
        else:
            if include_name == "False":
                include_name = False
            elif include_name == "True":
                include_name = True
            else:
                return Response("Параметр include_name передан неверно. Введите True или False",
                                status=status.HTTP_400_BAD_REQUEST)

        if include_code is None:
            include_code = False
        else:
            if include_code == "False":
                include_code = False
            elif include_code == "True":
                include_code = True
            else:
                return Response("Параметр include_code передан неверно. Введите True или False",
                                status=status.HTTP_400_BAD_REQUEST)

        if include_first_comment is None:
            include_first_comment = False
        else:
            if include_first_comment == "False":
                include_first_comment = False
            elif include_first_comment == "True":
                include_first_comment = True
            else:
                return Response("Параметр include_first_comment передан неверно. Введите True или False",
                                status=status.HTTP_400_BAD_REQUEST)

        if include_last_comment is None:
            include_last_comment = False
        else:
            if include_last_comment == "False":
                include_last_comment = False
            elif include_last_comment == "True":
                include_last_comment = True
            else:
                return Response("Параметр include_last_comment передан неверно. Введите True или False",
                                status=status.HTTP_400_BAD_REQUEST)

        if include_last_event_comment is None:
            include_last_event_comment = False
        else:
            if include_last_event_comment == "False":
                include_last_event_comment = False
            elif include_last_event_comment == "True":
                include_last_event_comment = True
            else:
                return Response("Параметр include_last_event_comment передан неверно. Введите True или False",
                                status=status.HTTP_400_BAD_REQUEST)

        context = {"include_code": include_code, "include_name": include_name,
                   "include_first_comment": include_first_comment,
                   "include_last_comment": include_last_comment,
                   "include_last_event_comment": include_last_event_comment}

        if transaction_id is not None:
            try:
                transaction = Transaction.objects.get(id=transaction_id)
                serializer = TransactionStatisticsSerializer([transaction], many=True, context=context)
                return Response(serializer.data)
            except Transaction.DoesNotExist:
                return Response("Переданный идентификатор не относится "
                                "ни к одной транзакции",
                                status=status.HTTP_404_NOT_FOUND)
        return Response("Не передан параметр transaction_id",
                        status=status.HTTP_400_BAD_REQUEST)


@api_view(http_method_names=['GET'])
@authentication_classes([authentication.SessionAuthentication,
                         authentication.TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_transaction_list_by_period(request, period_id):
    period = get_object_or_404(Period, pk=period_id)
    transactions_queryset = Transaction.objects.filter_by_period(request.user, period)
    serializer = TransactionFullSerializer(transactions_queryset, many=True, context={"user": request.user})
    return Response(serializer.data)
