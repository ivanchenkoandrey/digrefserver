import os
from pathlib import Path

import environ
from celery.schedules import crontab
import auth_app.tasks

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env()

SECRET_KEY = env('SECRET_KEY')
BOT_TOKEN = env('BOT_TOKEN')
DEBUG = True
ALLOWED_HOSTS = env('ALLOWED_HOSTS').split()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'auth_app.apps.AuthAppConfig',
    'corsheaders',
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'digrefserver.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'digrefserver.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL')
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication'
    ]
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(
    BASE_DIR, 'media'
)

CORS_ORIGIN_ALLOW_ALL = True

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} || {asctime} || {message}',
            'style': '{',
            'datefmt': '%d.%m.%Y %H:%M:%S',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'app_logs/thanks.log'),
            'maxBytes': 1024 * 50,
            'backupCount': 10,
            'formatter': 'simple',
        },
    },
    'loggers': {
        'auth_app': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'utils.accounts_data': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'utils.query_debugger': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

CELERY_BEAT_SCHEDULE = {
    "validate_transactions_after_grace_period": {
        "task": "auth_app.tasks.validate_transactions_after_grace_period",
        "schedule": crontab(minute="*"),
    }
}

GRACE_PERIOD = 60 * 10  # 10 minutes
ANONYMOUS_MODE = False

DEFAULT_USER_PASSWORD = env('DEFAULT_USER_PASSWORD')

EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = 2525
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

DATETIME_INPUT_FORMATS = [
    '%Y-%m-%d %H:%M:%S',  # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M:%S.%f',  # '2006-10-25 14:30:59.000200'
    '%Y-%m-%d %H:%M',  # '2006-10-25 14:30'
    '%Y-%m-%d',  # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',  # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M:%S.%f',  # '10/25/2006 14:30:59.000200'
    '%m/%d/%Y %H:%M',  # '10/25/2006 14:30'
    '%m/%d/%Y',  # '10/25/2006'
    '%m/%d/%y %H:%M:%S',  # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M:%S.%f',  # '10/25/06 14:30:59.000200'
    '%m/%d/%y %H:%M',  # '10/25/06 14:30'
    '%m/%d/%y',  # '10/25/06'
]
