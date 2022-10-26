import firebase_admin
from django.conf import settings
from firebase_admin import credentials

cred = credentials.Certificate(settings.CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
