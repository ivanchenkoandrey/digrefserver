import logging
import os.path
from datetime import timedelta

import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from auth_app.models import Account, UserStat
from utils.current_period import get_current_period

User = get_user_model()

logger = logging.getLogger(__name__)


def processing_accounts_data(user: User):
    queryset = Account.objects.filter(account_type__in=['I', 'D', 'F'], owner=user)
    period = get_current_period()
    user_stat = UserStat.objects.filter(user=user, period=period).first()
    expire_date = (timezone.now() + timedelta(days=5)).replace(hour=0, minute=0, second=0, microsecond=0)
    user_accounts_data = {
        "income": {
            "amount": queryset.filter(account_type='I').first().amount,
            "frozen": queryset.filter(account_type='F').first().amount,
            "sent": user_stat.income_used_for_thanks,
            "received": user_stat.income_thanks,
            "cancelled": user_stat.income_declined,
        }
    }
    distr_account = queryset.filter(account_type='D').first()
    if distr_account is not None:
        distr_data = {
            "distr": {
                "amount": distr_account.amount,
                "frozen": queryset.filter(account_type='F').first().amount,
                "sent": user_stat.distr_redist,
                "received": user_stat.distr_initial,
                "cancelled": user_stat.distr_declined,
                "expire_date": period.end_date
            }
        }
        user_accounts_data.update(distr_data)
    else:
        with open(os.path.join(settings.BASE_DIR, 'utils', 'distr_data.yml'), "r") as stream:
            try:
                default_distr_info = yaml.safe_load(stream)
                user_accounts_data.update(default_distr_info)
            except yaml.YAMLError:
                logger.error(f'Ошибка чтения файла настроек баланса по умолчанию')
    return user_accounts_data
