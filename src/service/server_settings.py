from .base_settings import *

# Host
ALLOWED_HOSTS = ["kbpo.stanford.edu", "171.64.67.11"]
MTURK_TARGET = 'actual'
#MTURK_TARGET = 'sandbox'
MTURK_FORM_TARGET = MTURK_FORM_TARGETS[MTURK_TARGET]
MTURK_HOST = 'https://kbpo.stanford.edu'
MTURK_FORCED=True

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
LOGGING['handlers']['file']['filename'] = '/data/kbpo/web/all.log'
LOGGING['handlers']['django']['filename'] = '/data/kbpo/web/django.log'
LOGGING['handlers']['kbpo']['filename'] = '/data/kbpo/web/kbpo.log'
LOGGING['handlers']['celery']['filename'] = '/data/kbpo/web/celery.log'

# Logging
LOGGING["handlers"]["email"] = {
    'level': 'ERROR',
    'class': 'web.logging.CustomSMTPHandler',
    'mailhost': (EMAIL_HOST, EMAIL_PORT),
    'fromaddr': DEFAULT_FROM_EMAIL,
    'toaddrs': ["admin@kbpo.stanford.edu"],
    'subject': 'ERROR on kbpo.stanford.edu',
    'secure': (),
    }
LOGGING["root"]["handlers"] += ["email"]
