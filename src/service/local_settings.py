from .base_settings import *

# Debug
ALLOWED_HOSTS = ["localhost"]
DEBUG = True
MTURK_TARGET = 'sandbox'
MTURK_FORM_TARGET = MTURK_FORM_TARGETS[MTURK_TARGET]
MTURK_HOST = 'https://localhost:8000'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    'test': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kbpo_test',
        'USER': 'kbpo',
        'PASSWORD': 'kbpo',
        'HOST': 'localhost',
        'PORT': 5433, # Tunnel to kbpo.stanford.edu
    },
    'production': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kbpo',
        'USER': 'kbpo',
        'PASSWORD': 'kbpo',
        'HOST': 'localhost',
        'PORT': 5433, # Tunnel to kbpo.stanford.edu
    },
}
DATABASES['default'] = DATABASES['test']

# Logging
LOGGING["handlers"]["email"] = {
    'level': 'ERROR',
    'class': 'web.logging.CustomSMTPHandler',
    'mailhost': (EMAIL_HOST, EMAIL_PORT),
    'fromaddr': DEFAULT_FROM_EMAIL,
    'toaddrs': ADMINS,
    'subject': 'ERROR with kbpo-local',
    'secure': (),
    }
# No need to spam us during development.
#LOGGING["root"]["handlers"] += ["email"]
