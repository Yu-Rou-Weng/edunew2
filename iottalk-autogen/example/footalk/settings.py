import os

from .settings import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'my_very_secret_code'

INSTALLED_APPS += [
    'footalk.apps.FootalkConfig',
]

ROOT_URLCONF = 'footalk.urls'

AG_API_URL = 'http://localhost:8081'
