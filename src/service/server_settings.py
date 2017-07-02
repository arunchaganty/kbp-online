from .base_settings import *

# Host
ALLOWED_HOSTS = ["kbpo.stanford.edu"]
#MTURK_TARGET = 'actual'
MTURK_TARGET = 'sandbox'
MTURK_FORM_TARGET = MTURK_FORM_TARGETS[MTURK_TARGET]
MTURK_HOST = 'https://kbpo.stanford.edu'

# Debug
DEBUG = False

# Location
STATIC_ROOT = "/data/kbpo/web/static"
MEDIA_ROOT = "/data/kbpo/web/media"

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'test': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kbpo_test',
        'USER': 'kbpo',
        'PASSWORD': 'kbpo',
        'HOST': 'localhost',
        'PORT': 5432, # Linked to KBPO.stanford.edu
    },
    'production': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kbpo',
        'USER': 'kbpo',
        'PASSWORD': 'kbpo',
        'HOST': 'localhost',
        'PORT': 5432, # Linked to KBPO.stanford.edu
    },
}
DATABASES['default'] = DATABASES['production']

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)-8s %(name)-15s %(message)s',
            'datefmt' : '%Y-%m-%d %H:%M:%S',
            }
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/data/kbpo/web/all.log',
            'formatter': 'default',
        },
        'django': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/data/kbpo/web/django.log',
            'formatter': 'default',
        },
        'kbpo': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/data/kbpo/web/kbpo.log',
            'formatter': 'default',
        },
        'celery': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/data/kbpo/web/celery.log',
            'formatter': 'default',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'django'],
            'level': 'INFO',
            'propagate': True,
        },
        'kbpo': {
            'handlers': ['file', 'kbpo'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'web': {
            'handlers': ['file', 'kbpo'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'celery': {
            'handlers': ['file', 'celery'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'root': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Host for sending e-mail.
EMAIL_HOST = 'localhost'

# Port for sending e-mail.
EMAIL_PORT = 1025

# Optional SMTP authentication information for EMAIL_HOST.
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
