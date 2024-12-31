import json

from json.decoder import JSONDecodeError

from .exceptions import JsonBadRequest


class JsonRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'application/json' in request.headers.get('Content-Type', ''):
            try:
                request.json = json.loads(request.body.decode('utf-8'))
            except JSONDecodeError:
                return JsonBadRequest('invalid JSON payload').response
        else:
            request.json = None
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, JsonBadRequest):
            return exception.response
        return None
