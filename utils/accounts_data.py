import logging
import os.path

import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from auth_app.models import Account, UserStat, Period
from utils.current_period import get_period

User = get_user_model()

logger = logging.getLogger(__name__)


def processing_accounts_data(user: User, period_id=None):
    if period_id is not None:
        period = get_object_or_404(Period, pk=period_id)
    else:
        period = get_period()
    queryset = Account.objects.filter(owner=user, challenge_id=None, organization_id=None)
    accounts_data = {f"{item.to_json().get('account_type')}": item.to_json() for item in queryset}
    user_stat = UserStat.objects.filter(user=user, period=period).first()
    user_profile_data = {
        "income": {
            "amount": accounts_data.get('I').get('amount'),
            "frozen": accounts_data.get('F').get('amount'),
            "sent": 0 if not user_stat else user_stat.income_used_for_thanks + user_stat.sent_to_challenges_from_income,
            "received": 0 if not user_stat else user_stat.income_thanks,
            "cancelled": 0 if not user_stat else user_stat.income_declined
        }
    }
    distr_account = accounts_data.get('D')
    if distr_account is not None:
        distr_data = {
            "distr": {
                "amount": accounts_data.get('D').get('amount'),
                "frozen": accounts_data.get('F').get('amount'),
                "sent": 0 if not user_stat else user_stat.distr_thanks + user_stat.sent_to_challenges,
                "received": 0 if not user_stat else user_stat.distr_initial,
                "cancelled": 0 if not user_stat else user_stat.distr_declined,
                "expire_date": None if not period else period.end_date
            }
        }
        user_profile_data.update(distr_data)
        if period_id is not None:
            distr_data.get("distr").update({"burnt": user_stat.distr_burnt})
            user_profile_data.update({"bonus": user_stat.bonus})
            user_profile_data['income'].update({'used_for_bonus': user_stat.income_used_for_bonus})
    else:
        with open(os.path.join(settings.BASE_DIR, 'utils', 'distr_data.yml'), "r") as stream:
            try:
                default_distr_info = yaml.safe_load(stream)
                user_profile_data.update(default_distr_info)
            except yaml.YAMLError:
                logger.error(f'Ошибка чтения файла настроек баланса по умолчанию')
    return user_profile_data
