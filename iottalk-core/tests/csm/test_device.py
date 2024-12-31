import json
import pytest

from uuid import UUID, uuid4

from iot import events
from iot.config import config
from iot.conn import IoTConnMgr
from iot.csm import device


@pytest.fixture()
def dev(db):
    def req(callback):
        pass

    def res(payload):
        return payload

    req.remove_callback = (lambda: None)

    d = device.Device(req, res)
    yield d


@pytest.fixture(
    params=[
        events.DevAppOnline,
        events.DevAppOffline,
    ])
def event(request, dev, alphacat_id):
    yield request.param(UUID(alphacat_id))


@pytest.fixture
def conn_mgr(monkeypatch):
    conf = config.mqtt_conf
    i = IoTConnMgr(auto_connect=False)
    i.setup_conn('mqtt', conf['host'], port=conf['port'], client_id=uuid4())

    assert i.mqtt_c
    assert i.mqtt_connected

    monkeypatch.setattr('iot.csm.device.iot_conn_mgr', i)
    yield i


@pytest.mark.parametrize('id, res', [
    (uuid4(), {}),
    (UUID('a54b5bf9-c39b-4248-b611-80d1ed4a36df'), {
        'a54b5bf9-c39b-4248-b611-80d1ed4a36df': {
            'id': 'a54b5bf9-c39b-4248-b611-80d1ed4a36df',
            'name': 'AlphaCat',
            'idf_list': [['meow', ['dB']]],
            'state': 'offline',
            'rev': 'cc35867e-1f74-47d3-88c9-7dcc374a5919',
            'profile': {
                'model': 'AI',
            }
        }
    }),
])
def test_snapshot(dev, conn_mgr, id, res):
    s = dev.snapshot
    assert s == {}

    conn_mgr.mqtt_ctrl(id, 'not_important', 'not_important', '42')
    s = dev.snapshot

    assert json.dumps(s)

    if not res:
        return

    x = s[str(id)]
    assert isinstance(x.pop('register_time'), float)
    assert s == res, s


def test_attach(dev, conn_mgr):
    res = dev.attach()

    assert json.dumps(res)
    assert res.get('op') == 'attach'
    assert res.get('state') == 'ok'
    assert res.get('da_list') == {}


def test_anno_(dev, alphacat_id, event):
    res = dev.anno(event)

    assert json.dumps(res)
    assert res.get('op') == 'anno'
    assert res.get('type') == event.type
    assert res.get('timestamp') == str(event.timestamp)
    assert res.get('da')
