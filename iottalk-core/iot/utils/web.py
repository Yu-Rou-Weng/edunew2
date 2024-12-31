from tornado.web import RequestHandler
from tornado.escape import json_decode, json_encode


class JSONHandler(RequestHandler):

    def prepare(self):
        if self.request.method in ('GET', 'OPTIONS', 'HEAD'):
            return

        content_type = self.request.headers.get('Content-Type', '')

        if not content_type == 'application/json':
            self.send_error(
                400,
                msg='content type not supported: {!r}'.format(
                    content_type))

        try:
            self.json = json_decode(self.request.body)
        except ValueError:
            self.send_error(400, msg='json decode error')

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')
        # CROS support
        # https://developer.mozilla.org/zh-TW/docs/HTTP/Access_control_CORS
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers',
                        'Accept, Content-Type')
        self.set_header('Access-Control-Allow-Methods',
                        'POST, PUT, DELETE, GET, OPTIONS')

    def options(self, *args, **kwargs):
        '''
        simple OPTIONS for CROS support
        '''
        self.set_status(204)
        self.finish()

    def write(self, obj):
        '''
        Write a dictionary as json to response
        '''
        if not isinstance(obj, dict):
            raise TypeError('Object {!r} is not a dict'.format(obj))

        super(JSONHandler, self).write(json_encode(obj))
        self.finish()

    def write_error(self, status_code, msg=None, **kwargs):
        self.write({
            'state': 'error',
            'reason': msg or 'unknown',
        })
