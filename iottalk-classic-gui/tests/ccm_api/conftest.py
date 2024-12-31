import json
import uuid

from functools import partial
from pathlib import Path

import pytest

from paho.mqtt.publish import single as mqtt_pub

from iotgui import db, config
from iotgui.ccm import mqttclient
from iotgui.ccm.server import app as flask_app

from .utils import block_sub


@pytest.fixture
def mqtt_pub_json():
    def f(topic, payload, *args, **kwargs):
        return mqtt_pub(topic, json.dumps(payload), *args, **kwargs)

    return f


@pytest.fixture
def client_id():
    return str(uuid.uuid4())


@pytest.fixture
def pub_topic(client_id):
    return 'iottalk/api/gui/req/{}'.format(client_id)


@pytest.fixture
def pub(pub_topic, mqtt_pub_json):
    return partial(mqtt_pub_json, pub_topic)


@pytest.fixture
def sub_topic(client_id):
    return 'iottalk/api/gui/res/{}'.format(client_id)


@pytest.fixture
def sub(request, sub_topic):
    """
    This is block by ``block_sub``
    """
    mqtt_client, userdata = block_sub(sub_topic)

    # finalizer
    def fin():
        mqtt_client.disconnect()
        mqtt_client.loop_stop()

    request.addfinalizer(fin)
    return userdata


@pytest.fixture
def http_client(tmp_path):
    db_path = tmp_path / 'iottalk-gui.db'
    flask_app.config['TESTING'] = True
    flask_app.secret_key = 'dev'
    client = flask_app.test_client()

    config.DB_URL = 'sqlite+pysqlite:///{}'.format(db_path)
    db.migrate()
    db.connect()

    # start CCM module
    mqttclient.init()

    yield client

    # Remove the temporary directory
    Path(db_path).unlink()
    db.engine = None
    mqttclient.mqtt_module.cleanup()


@pytest.fixture
def account(http_client, api_root):
    '''
    create a new account and sign in
    '''
    acc = {
        'username': 'test',
        'password': 'dev',
    }
    res = http_client.post('{}/account/create/'.format(api_root), json=acc)
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'id' in res.json
    uid = res.json['id']

    res = http_client.post('{}/account/login/'.format(api_root), json=acc)
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'id' in res.json
    assert uid == res.json['id']

    acc['id'] = uid
    yield acc


@pytest.fixture
def api_root():
    '''
    API root URL
    '''
    return '/api/v0'


@pytest.fixture
def sample_dfs(http_client, account, api_root):
    res = http_client.put('{}/devicefeature/'.format(api_root), json={
        'df_type': 'input',
        'df_name': 'foo',
        'df_parameter': [{}, {}, {}],
    })
    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert 'df_id' in res.json
    foo_id = res.json['df_id']

    res = http_client.put('{}/devicefeature/'.format(api_root), json={
        'df_type': 'output',
        'df_name': 'bar',
        'df_parameter': [{}],
    })
    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert 'df_id' in res.json
    bar_id = res.json['df_id']

    return foo_id, bar_id


@pytest.fixture
def sample_dms(http_client, sample_dfs, api_root):
    res = http_client.put('{}/devicemodel/'.format(api_root), json={
        "dm_name": "FooModel",
        "df_list": [
            {
                "df_id": sample_dfs[0],
                "df_parameter": [{}]
            },
            {
                "df_id": sample_dfs[1],
                "df_parameter": [{}]
            }
        ]
    })
    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert 'dm_id' in res.json
    foo_id = res.json['dm_id']

    res = http_client.put('{}/devicemodel/'.format(api_root), json={
        "dm_name": "BarModel",
        "df_list": [
            {
                "df_id": sample_dfs[0],
                "df_parameter": [{}]
            },
            {
                "df_id": sample_dfs[1],
                "df_parameter": [{}]
            }
        ]
    })
    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert 'dm_id' in res.json
    bar_id = res.json['dm_id']

    return foo_id, bar_id


@pytest.fixture
def plan9(http_client, account, api_root):
    res = http_client.put('{}/project/'.format(api_root), json={
        "p_name": "plan9",
    })

    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert res.json['p_id']

    yield res.json['p_id']


@pytest.fixture
def sample_dos(http_client, api_root, plan9, sample_dms, sample_dfs):
    '''sample Device Objects'''
    foo_dm, bar_dm = sample_dms

    res = http_client.put('{}/project/{}/deviceobject/'.format(api_root, plan9),
                          json={'dm_id': foo_dm, 'df': sample_dfs})
    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert 'do_id' in res.json
    foo_id = res.json['do_id']

    res = http_client.put('{}/project/{}/deviceobject/'.format(api_root, plan9),
                          json={'dm_id': bar_dm, 'df': sample_dfs})
    assert res.status_code == 201
    assert res.json['state'] == 'ok'
    assert 'do_id' in res.json
    bar_id = res.json['do_id']

    return foo_id, bar_id


@pytest.fixture
def sample_nas(http_client, api_root, sample_dos, plan9):
    res = http_client.get('{}/project/{}/'.format(api_root, plan9))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    dfo_ids = [data['ido'][0]['dfo'][0]['dfo_id'],
               data['odo'][0]['dfo'][0]['dfo_id']]

    res = http_client.put('{}/project/{}/na/'.format(api_root, plan9), json={
        'na_name': 'JoinFoo',
        'na_idx': 0,
        'dfo_ids': dfo_ids,
    })
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    foo_id = res.json['na_id']

    res = http_client.put('{}/project/{}/na/'.format(api_root, plan9), json={
        'na_name': 'JoinBar',
        'na_idx': 1,
        'dfo_ids': dfo_ids,
    })
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    bar_id = res.json['na_id']

    return foo_id, bar_id
