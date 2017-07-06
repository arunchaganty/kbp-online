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
    'class': 'logging.handlers.SMTPHandler',
    'mailhost': 'localhost',
    'fromaddr': 'admin@kbpo.stanford.edu',
    'toaddrs': ['chaganty@stanford.edu', 'ashwinpp@stanford.edu', 'kbp-online-admin@lists.stanford.edu'],
    'subject': 'ERROR with kbpo-local',
    }
LOGGING["root"]["handlers"] += ["email"]
