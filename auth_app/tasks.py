from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def make_log_message():
    logger.info(f'Task successfully done')
