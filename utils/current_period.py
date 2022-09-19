import datetime
from django.db.models import Q

from auth_app.models import Period
from django.utils import timezone


def get_current_period():
    now = timezone.now()
    current_period = Period.objects.filter(
        Q(start_date__lte=now) & Q(end_date__gte=now)).first()
    return current_period


def get_period() -> Period:
    today = datetime.date.today()
    current_period = Period.objects.filter(
        Q(start_date__lte=today) & Q(end_date__gte=today)).first()
    if current_period is None:
        previous_period = (Period.objects.filter(end_date__lt=today)
                           .order_by('-end_date').first())
        return previous_period
    return current_period
