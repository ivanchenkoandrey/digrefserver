import logging

from rest_framework import authentication
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Period
from utils.custom_permissions import (IsOrganizationAdmin, IsDepartmentAdmin,
                                      IsSystemAdmin)
from .serializers import PeriodSerializer
from .service import (get_period, _get_period_by_date,
                      get_periods_list, NotADateError,
                      WrongDateFormatError, PeriodDoesntExistError)

logger = logging.getLogger(__name__)


class PeriodListView(ListAPIView):
    """
    Возвращает список периодов, в которые осуществлялась раздача спасибок
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    serializer_class = PeriodSerializer
    queryset = Period.objects.all()


class CreatePeriodView(APIView):
    """
    Создаёт период (только администратор организации верхнего уровня)
    """
    authentication_classes = [authentication.SessionAuthentication,
                              authentication.TokenAuthentication]
    permission_classes = [IsSystemAdmin | IsOrganizationAdmin |
                          IsDepartmentAdmin]

    @classmethod
    def post(cls, request, *args, **kwargs):
        serializer = PeriodSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)


@api_view(http_method_names=['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([authentication.SessionAuthentication,
                        authentication.TokenAuthentication])
def get_current_period(request):
    """
    Возвращает текущий периода либо, если текущий период не задан,
    то предыдущий
    """
    period = get_period()
    response = Response(period)
    if 'period_id' not in request.COOKIES:
        set_period_cookies(period, response)
    else:
        logger.info(f"ID периода: {type(request.COOKIES.get('period_id'))}")
        if request.COOKIES.get('period_id') != period.get('id'):
            set_period_cookies(period, response)
    return response


def set_period_cookies(period, response):
    """
    Установка кук для быстрого получения информации о периоде
    без дополнительного запроса в БД
    """
    cookie_max_age = 3600 * 24 * 14
    response.set_cookie('period_id', period.get('id'), max_age=cookie_max_age)
    response.set_cookie('period_start_date', period.get('start_date'), max_age=cookie_max_age)
    response.set_cookie('period_end_date', period.get('end_date'), max_age=cookie_max_age)
    response.set_cookie('period_organization_id', period.get('organization_id'), max_age=cookie_max_age)


@api_view(http_method_names=['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([authentication.SessionAuthentication,
                        authentication.TokenAuthentication])
def get_period_by_date(request):
    """
    Возвращает период, в котором была искомая дата
    """
    try:
        period = _get_period_by_date(request.data.get('date', ''))
        return Response(period)
    except NotADateError:
        return Response('Дата не была передана', status=status.HTTP_400_BAD_REQUEST)
    except WrongDateFormatError:
        return Response('Формат даты: YYYY-MM-DD', status=status.HTTP_400_BAD_REQUEST)
    except PeriodDoesntExistError:
        return Response('Период не найден', status=status.HTTP_404_NOT_FOUND)


@api_view(http_method_names=['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([authentication.SessionAuthentication,
                        authentication.TokenAuthentication])
def get_periods(request):
    """
    Возвращает список периодов, начиная с указанной даты
    """
    date_from = request.data.get('from_date', '')
    limit = request.data.get('limit', 10)
    try:
        if date_from is not None:
            if isinstance(limit, int) and 0 < int(limit) < 11:
                periods_list = get_periods_list(date_from, limit)
            else:
                return Response('Лимит должен быть числом от 1 до 10',
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            periods_list = get_periods_list(date_from, limit)
        return Response(periods_list)
    except NotADateError:
        return Response('Дата не была передана', status=status.HTTP_400_BAD_REQUEST)
    except WrongDateFormatError:
        return Response('Формат даты: YYYY-MM-DD', status=status.HTTP_400_BAD_REQUEST)
