from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone


def processing_accounts_data(queryset: QuerySet):
    expire_date = (timezone.now() + timedelta(days=5)).replace(hour=0, minute=0, second=0, microsecond=0)
    accounts_types = {"I": "income", "D": "distr"}
    user_accounts_data = {
        "income": {
            "amount": 0,
            "frozen": 0,
            "sended": 0,
            "received": 0,
            "cancelled": 0,
        },
        "distr": {
            "amount": 0,
            "expire_date": expire_date,
            "frozen": 0,
            "sended": 0,
            "received": 0,
            "cancelled": 0,
        }}
    if len(queryset):
        for item in queryset:
            user_accounts_data[accounts_types[item.account_type]]["amount"] = item.amount
            user_accounts_data[accounts_types[item.account_type]]["received"] = item.amount
            user_accounts_data[accounts_types[item.account_type]]["frozen"] = item.frozen
    return user_accounts_data
