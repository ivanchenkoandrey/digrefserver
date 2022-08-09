from __future__ import absolute_import, unicode_literals

import logging
from django.core.mail import send_mail

from digrefserver.celery import app

logger = logging.getLogger(__name__)


@app.task
def make_log_message():
    logger.info(f'Task successfully done')


@app.task
def send(user_email: str, code: str) -> None:
    send_mail(
        'Подтверждение входа в сервис Цифровое Спасибо',
        f'Вы запросили пароль для входа в сервис Цифровое спасибо.\nВаш код доступа: {code}',
        'test_mobile_thanks@mail.ru',
        [user_email],
        fail_silently=False,
    )
