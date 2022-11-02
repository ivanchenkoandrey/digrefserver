import logging

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

cred = credentials.Certificate(settings.CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)

logger = logging.getLogger(__name__)


def send_push(title, msg, registration_token, data_object=None):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=msg
        ),
        data=data_object,
        token=registration_token
    )
    messaging.send(message)


def send_multiple_push(title, msg, tokens, data_object=None):
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=msg),
        data=data_object,
        tokens=tokens
    )
    messaging.send_multicast(message)
