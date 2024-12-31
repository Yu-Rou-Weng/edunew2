import json
import pytest

from tornado.httpclient import HTTPError
from tornado.web import Application

from iot.utils.web import JSONHandler


class EchoHandler(JSONHandler):
    def get(self):
        self.write({
            'status': 'ok',
            'method': 'GET',
        })

    def options(self):
        self.write({
            'status': 'ok',
            'method': 'OPTIONS',
        })

    def head(self):
        self.write({
            'status': 'ok',
            'method': 'HEAD',
        })

    def post(self):
        assert self.json == {'answer': 42}

        self.write({
            'status': 'ok',
            'method': 'POST',
        })

    def put(self):
        assert self.json == {'answer': 42}

        self.write({
            'status': 'ok',
            'method': 'PUT',
        })

    def delete(self):
        self.write({
            'status': 'ok',
            'method': 'DELETE',
        })

    def patch(self):
        self.write({
            'status': 'ok',
            'method': 'PATCH',
        })


class BrokenHandler(JSONHandler):
    def get(self):
        self.write('magic')


@pytest.fixture()
def app():
    return Application([
        (r'/', EchoHandler),
        (r'/broken', BrokenHandler),
    ])


@pytest.fixture()
def json_payload():
    return json.dumps({'answer': 42})


@pytest.fixture(params=('GET', 'HEAD', 'OPTIONS'))
def light_method(request):
    return request.param


@pytest.fixture(params=('POST', 'PUT', 'PATCH', 'DELETE'))
def heavy_method(request):
    return request.param


@pytest.mark.gen_test
def test_json_handler_light_method(http_client, base_url, light_method):
    '''
    JSONHandler do not care ``Content-Type`` on ``light_method``
    '''
    response = yield http_client.fetch(base_url, method=light_method)
    assert response.code == 200

    if light_method == 'HEAD':
        return

    result = json.loads(response.body.decode('utf-8'))
    assert result['status'] == 'ok'
    assert result['method'] == light_method


@pytest.mark.gen_test
def test_json_handler_heavy_method(http_client, base_url, json_header,
                                   json_payload, heavy_method):
    response = yield http_client.fetch(base_url, method=heavy_method,
                                       headers=json_header, body=json_payload,
                                       allow_nonstandard_methods=True)
    assert response.code == 200

    result = json.loads(response.body.decode('utf-8'))
    assert result['status'] == 'ok'
    assert result['method'] == heavy_method


@pytest.mark.gen_test
def test_json_handler_invalid_content_type(
        http_client, base_url, json_payload, heavy_method):
    headers = {
        'Content-Type': 'universe/answer',
    }
    with pytest.raises(HTTPError) as err:
        yield http_client.fetch(base_url, method=heavy_method,
                                body=json_payload, headers=headers,
                                allow_nonstandard_methods=True)

    code, _, res = err.value.args
    result = json.loads(res.body.decode('utf-8'))

    assert code == 400
    assert result['state'] == 'error'
    assert 'universe/answer' in result['reason']


@pytest.mark.gen_test
def test_json_handler_post_invalid_body(
        http_client, base_url, json_header, heavy_method):
    with pytest.raises(HTTPError) as err:
        yield http_client.fetch(base_url, method=heavy_method,
                                headers=json_header, body='magic',
                                allow_nonstandard_methods=True)

    code, _, res = err.value.args
    result = json.loads(res.body.decode('utf-8'))

    assert code == 400
    assert result['state'] == 'error'
    assert 'decode error' in result['reason']


@pytest.mark.gen_test
def test_invalid_write(http_client, base_url, json_header):
    url = '{}/broken'.format(base_url)
    with pytest.raises(HTTPError) as err:
        yield http_client.fetch(url, method='GET', headers=json_header)

    code, _, res = err.value.args
    result = json.loads(res.body.decode('utf-8'))

    assert code == 500
    assert result['state'] == 'error'
    assert result['reason'] == 'unknown'
