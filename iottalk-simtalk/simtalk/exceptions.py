import logging
import traceback

from io import StringIO

from django.http import JsonResponse

log = logging.getLogger('simtalk.exception')
log.setLevel(logging.DEBUG)


class CompilationError(Exception):
    pass


def raise_compilation_error():
    exc_output = StringIO()
    traceback.print_exc(file=exc_output)
    log.debug('User defined function exception:\n %s',
              exc_output.getvalue())
    raise CompilationError(exc_output.getvalue())


class JsonBadRequest(Exception):
    status = 400

    def __init__(self, reason: str, payload: dict = None):
        payload = {} if payload is None else payload
        assert 'state' not in payload, 'duplicate key `state` in payload'
        payload.update({
            'state': 'error',
            'reason': reason
        })
        self.payload = payload

    @property
    def response(self):
        return JsonResponse(self.payload, status=self.status)
