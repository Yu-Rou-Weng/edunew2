import os

import requests

from django.shortcuts import render
from django.http.response import HttpResponse
from django.conf import settings


def index(request):
    sa = os.path.join(settings.BASE_DIR, 'footalk', 'sa.py')
    code = open(sa).read()
    url = f'{settings.AG_API_URL}/create_device/'
    res = requests.post(url, json={'code': code, 'version': 2})
    assert res.status_code == 200
    return HttpResponse(res.text)
