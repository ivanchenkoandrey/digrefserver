import logging
from typing import Dict

from auth_app.models import Setting

logger = logging.getLogger(__name__)


def validate_anonymous_mode_request(request) -> bool:
    if request.data.get('anonymous_mode') in ('on', 'off'):
        return True
    logger.info(f'Неправильные данные в запросе смены режима анонимности: {request.data}')
    return False


def reset_anonymous_mode(setting: Setting, data: Dict) -> bool:
    mode = data.get('anonymous_mode')
    if mode == 'on':
        setting.value = 'on'
        setting.save(update_fields=['value'])
        logger.info('Настройка анонимности включена')
    elif mode == 'off':
        setting.value = 'off'
        setting.save(update_fields=['value'])
        logger.info('Настройка анонимности выключена')
    return True if mode == 'on' else False
