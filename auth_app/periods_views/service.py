from typing import Optional

from auth_app.models import Period
import datetime
from django.db.models import F, Q
from dateutil.parser import parse


class NotADateError(Exception):
    pass


class WrongDateFormatError(Exception):
    pass


class PeriodDoesntExistError(Exception):
    pass


def get_period_pk() -> int:
    today = datetime.date.today()
    current_period = Period.objects.filter(
        Q(start_date__lte=today) & Q(end_date__gte=today)).first()
    if current_period is None:
        previous_period = Period.objects.filter(end_date__lt=today).order_by('-end_date').first()
        return previous_period.pk
    return current_period.pk


def is_date(string: str, fuzzy=False) -> bool:
    try:
        parse(string, fuzzy=fuzzy)
        return True
    except ValueError:
        return False


def get_period_pk_by_date(date: str) -> int:
    if is_date(date):
        try:
            date_object = datetime.datetime.strptime(date, '%Y-%m-%d')
            period = Period.objects.filter(
                Q(start_date__lte=date) & Q(end_date__gte=date)).first()
            if period is not None:
                return period.pk
            else:
                raise PeriodDoesntExistError
        except ValueError:
            raise WrongDateFormatError
    else:
        raise NotADateError


def get_periods_list(from_date: Optional[str], limit: int):
    if is_date(from_date):
        try:
            today = datetime.date.today()
            date_object = datetime.datetime.strptime(from_date, '%Y-%m-%d')
            period_list = (Period.objects
                           .filter(Q(start_date__lte=from_date) & Q(start_date__lte=today))
                           .order_by('-end_date')[:limit]
                           .annotate(time_from=F('start_date'),
                                     time_to=F('end_date'))
                           .values('id', 'name', 'time_from', 'time_to'))
            return period_list
        except ValueError:
            raise WrongDateFormatError
    else:
        raise NotADateError
