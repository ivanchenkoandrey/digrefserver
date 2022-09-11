from django.db.models import Q

from auth_app.models import Period
from django.utils import timezone


def get_current_period():
    now = timezone.now()
    current_period = Period.objects.filter(
        Q(start_date__lte=now) & Q(end_date__gte=now)).first()
    return current_period
