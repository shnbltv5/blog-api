from settings import conf
from settings.base import *

DEBUG = False
ALLOWED_HOSTS = conf.ALLOWED_HOSTS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': conf.DB_NAME,
        'USER': conf.DB_USER,
        'PASSWORD': conf.DB_PASSWORD,
        'HOST': conf.DB_HOST,
        'PORT': conf.DB_PORT,
    }
}
