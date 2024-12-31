# -*- coding: utf-8 -*-
import json
import re

from uuid import uuid4

import pytest

from iot.raproto.http.app import mkapp, MQTTMixin


@pytest.fixture
def app(db):
    return mkapp()


@pytest.fixture(params=('BetaCat', u'貝塔貓'))
def beta_cat(request):
    return json.dumps({
        'name': request.param,
        'accept_protos': ['mqtt'],
        'idf_list': [['meow', ['dB']]],
        'profile': {
            'model': 'AI',
        },
    })


noname_ai = json.dumps({
    'accept_protos': ['mqtt'],
    'idf_list': [['meow', ['dB']]],
    'profile': {
        'model': 'AI',
    },
})
noname_nomodel = json.dumps({
    'accept_protos': ['mqtt'],
    'idf_list': [['meow', ['dB']]],
    'profile': {
        'model': 'BetaCat',
    },
})


@pytest.mark.gen_test(timeout=20)
@pytest.mark.parametrize('da, pattern',
                         [(noname_ai, r'^[\d]{2}\.AI$'),
                          (noname_nomodel, r'^[\d]{2}.BetaCat$')])
def test_generate_device_name(http_client, base_url, json_header, db, da,
                              pattern):
    for i in range(100):
        url = '{}/{}'.format(base_url, uuid4())
        res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                      body=da, raise_error=False)

        result = json.loads(res.body.decode('utf-8'))
        assert res.code == 200
        assert result['state'] == 'ok'
        assert re.match(pattern, result.get('name')) is not None

    url = '{}/{}'.format(base_url, uuid4())
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=da, raise_error=False)

    result = json.loads(res.body.decode('utf-8'))
    assert res.code == 510
    assert result['state'] == 'error'
    assert 'Name pool is full' in result['reason']


@pytest.mark.gen_test
def test_verify_put_data(http_client, base_url, json_header, uuid, db,
                         beta_cat):
    url = '{}/{}'.format(base_url, uuid)
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=beta_cat)

    result = json.loads(res.body.decode('utf-8'))
    assert result['state'] == 'ok'
    assert result['id'] == uuid

    assert 'ctrl_chans' in result
    assert isinstance(result['ctrl_chans'], list)

    assert 'url' in result
    assert isinstance(result['url'], dict)
    assert 'scheme' in result['url']
    assert 'host' in result['url']
    assert 'port' in result['url']


@pytest.mark.gen_test
def test_put_invalid_accept_protos_type(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': 42,
        'idf_list': [['meow', ['dB']]],
        'profile': {
            'model': 'BetaCat',
        },
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'accept_protos' in result['reason']


@pytest.mark.gen_test
def test_put_invalid_accept_protos_content(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': ['magic'],
        'idf_list': [['meow', ['dB']]],
        'profile': {
            'model': 'BetaCat',
        },
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'Invalid protocol' in result['reason']


@pytest.mark.gen_test
def test_put_invalid_empty_accept_protos(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': [],
        'idf_list': [['meow', ['dB']]],
        'profile': {
            'model': 'BetaCat',
        },
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'accept_protos' in result['reason']
    assert 'can not be empty' in result['reason']


@pytest.mark.gen_test
def test_put_invalid_idf_list_type(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': ['mqtt'],
        'idf_list': 42,
        'profile': {
            'model': 'BetaCat',
        },
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'idf_list' in result['reason']


@pytest.mark.gen_test
def test_put_invalid_empty_idf_list(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': ['mqtt'],
        'idf_list': [],
        'profile': {
            'model': 'BetaCat',
        },
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'idf_list' in result['reason']
    assert 'can not be empty' in result['reason']


@pytest.mark.gen_test
def test_put_invalid_profile(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': ['mqtt'],
        'profile': 42
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'profile' in result['reason']
    assert 'json' in result['reason']


@pytest.mark.gen_test
def test_put_unknown_field(
        http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    beta_cat = {
        'name': 'BetaCat',
        'accept_protos': ['mqtt'],
        'answer': 42,
        'profile': {
            'model': 'BetaCat',
        },
    }
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=json.dumps(beta_cat), raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 403
    assert result['state'] == 'error'
    assert 'Unknown field' in result['reason']
    assert 'answer' in result['reason']


@pytest.mark.gen_test
def test_put(http_client, base_url, json_header, uuid, db, beta_cat):
    url = '{}/{}'.format(base_url, uuid)

    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=beta_cat)
    assert res.code == 200

    result = json.loads(res.body.decode('utf-8'))

    assert result['state'] == 'ok'
    assert result['id'] == uuid
    assert isinstance(result['ctrl_chans'], list)
    assert len(result['ctrl_chans']) == 2
    assert isinstance(result['url'], dict)


@pytest.mark.gen_test
def test_put_uuid_rereg(
        http_client, base_url, json_header, uuid, db, beta_cat):
    url = '{}/{}'.format(base_url, uuid)
    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=beta_cat)
    assert res.code == 200
    result = json.loads(res.body.decode('utf-8'))
    rev_orig = result['rev']

    res = yield http_client.fetch(url, method='PUT', headers=json_header,
                                  body=beta_cat, raise_error=False)
    assert res.code == 200

    result = json.loads(res.body.decode('utf-8'))
    rev_new = result['rev']

    assert result['state'] == 'ok'
    assert rev_orig != rev_new


@pytest.mark.gen_test
def test_delete(http_client, base_url, json_header, alphacat_id, db):
    url = '{}/{}'.format(base_url, alphacat_id)
    body = {'rev': 'cc35867e-1f74-47d3-88c9-7dcc374a5919'}
    res = yield http_client.fetch(url, method='DELETE', headers=json_header,
                                  body=json.dumps(body),
                                  allow_nonstandard_methods=True)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 200
    assert result['state'] == 'ok'
    assert result['id'] == alphacat_id


@pytest.mark.gen_test
def test_delete_not_found(http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    body = {'rev': 'cc35867e-1f74-47d3-88c9-7dcc374a5919'}
    res = yield http_client.fetch(url, method='DELETE', headers=json_header,
                                  body=json.dumps(body), raise_error=False,
                                  allow_nonstandard_methods=True)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 404
    assert result['state'] == 'error'
    assert result['reason'] == 'id not found'


@pytest.mark.gen_test
def test_delete_miss_rev(http_client, base_url, json_header, alphacat_id, db):
    url = '{}/{}'.format(base_url, alphacat_id)
    res = yield http_client.fetch(url, method='DELETE', headers=json_header,
                                  body=json.dumps({}), raise_error=False,
                                  allow_nonstandard_methods=True)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 400
    assert result['state'] == 'error'
    assert 'revision' in result['reason']


@pytest.mark.gen_test
def test_get(http_client, base_url, json_header, alphacat_id, db):
    url = '{}/{}'.format(base_url, alphacat_id)
    res = yield http_client.fetch(url, headers=json_header)
    result = json.loads(res.body.decode('utf-8'))

    assert result['state'] == 'ok'
    assert result['id'] == alphacat_id
    assert result['name'] == 'AlphaCat'
    assert result['idf_list'] == [['meow', ['dB']]]
    assert result.get('accept_protos') is None
    assert result['rev'] == 'cc35867e-1f74-47d3-88c9-7dcc374a5919'
    assert result['profile'] == {'model': 'AI'}


@pytest.mark.gen_test
def test_get_not_found(http_client, base_url, json_header, uuid, db):
    url = '{}/{}'.format(base_url, uuid)
    res = yield http_client.fetch(url, headers=json_header, raise_error=False)
    result = json.loads(res.body.decode('utf-8'))

    assert res.code == 404
    assert result['state'] == 'error'
    assert result['reason'] == 'id not found'


def test_mqtt_conf():
    m = MQTTMixin()
    url = m.mqtt_url

    assert 'ws_scheme' in url
    assert 'ws_port' in url
    assert 'ws_host' not in url
