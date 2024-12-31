import json
import pytest
import requests

from threading import Thread, Lock
from time import sleep
from uuid import UUID

from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.testing import bind_unused_port

from paho.mqtt import client as mqtt

from iot.raproto.http.app import mkapp

from iottalkpy import dan as iot_dan


@pytest.fixture()
def _unused_port():
    return bind_unused_port()


@pytest.fixture()
def http_port(_unused_port):
    return _unused_port[1]


@pytest.fixture()
def base_url(http_port):
    return 'http://localhost:{}'.format(http_port)


@pytest.fixture()
def server(http_port, _unused_port, db):
    '''
    This fixture waits for the RAProto HTTP server starts up
    '''
    def start_server(lock):
        io_loop = IOLoop()
        io_loop.make_current()

        app = mkapp()
        server = HTTPServer(app)
        server.add_socket(_unused_port[0])

        io_loop.add_callback(lock.release)
        IOLoop.current(instance=False).start()

    lock = Lock()
    lock.acquire()

    t = Thread(target=start_server, args=(lock,))
    t.daemon = True
    t.start()

    lock.acquire()  # wait for server start
    yield t
    lock.release()


@pytest.fixture()
def dan(server):
    iot_dan._default_client = iot_dan.Client()  # refresh some global contexts
    yield iot_dan


@pytest.fixture()
def simple_da(dan, server, base_url):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )

    assert context.rev is not None
    yield context
    sleep(1)  # make DA busy
    dan.deregister()


def test_register_without_id(server, base_url, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=[('acce', ['m/s^s', 'm/s^2', 'm/s^2'])],
        odf_list=[('meow', ['dB'])],
        name='test da',
        profile={
            'model': 'BetaCat',
        },
    )

    assert context.url == base_url
    assert context.rev is not None
    assert isinstance(context.app_id, UUID)
    assert context.mqtt_host is not None
    assert context.mqtt_port is not None
    assert isinstance(context.mqtt_client, mqtt.Client)
    assert context.on_signal is on_signal
    assert context.on_data is on_data

    sleep(1)  # make DA busy


def test_register_with_id(server, base_url, uuid, uuid_obj, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        id_=uuid,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=[('acce', ['m/s^s', 'm/s^2', 'm/s^2'])],
        odf_list=[('meow', ['dB'])],
        name='test da',
        profile={
            'model': 'BetaCat',
        },
    )

    assert context.url == base_url
    assert context.rev is not None
    assert context.app_id == uuid_obj
    assert context.mqtt_host is not None
    assert context.mqtt_port is not None
    assert isinstance(context.mqtt_client, mqtt.Client)
    assert context.on_signal is on_signal
    assert context.on_data is on_data

    sleep(1)  # make DA busy


def test_register_deregister(server, base_url, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=[('acce', ['m/s^s', 'm/s^2', 'm/s^2'])],
        odf_list=[('meow', ['dB'])],
        name='test da',
        profile={
            'model': 'BetaCat',
        },
    )

    assert context.url == base_url
    assert context.rev is not None
    assert isinstance(context.app_id, UUID)
    assert context.mqtt_host is not None
    assert context.mqtt_port is not None
    assert isinstance(context.mqtt_client, mqtt.Client)
    assert context.on_signal is on_signal
    assert context.on_data is on_data

    sleep(1)  # make DA busy
    dan.deregister()

    assert context.mqtt_client is None


def test_register_profile(server, base_url, uuid, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        id_=uuid,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )

    assert context.rev is not None

    url = '{}/{}'.format(base_url, uuid)
    res = requests.get(url)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data['id'] == uuid
    assert data['profile'] == {'model': 'AI'}

    sleep(1)  # make DA busy


def test_mqtt_online_msg(mqtt_client, simple_da, lock, dan):
    topic = simple_da.i_chans['ctrl']
    rev = simple_da.rev

    def on_msg(client, user_data, msg):
        on_msg.topic = msg.topic
        on_msg.payload = json.loads(msg.payload.decode())
        lock.release()

    mqtt_client.on_message = on_msg
    mqtt_client.subscribe(topic)

    lock.acquire()  # wait for message

    assert topic == on_msg.topic
    assert on_msg.payload == {
        'state': 'online',
        'rev': rev,
    }


def test_mqtt_offline_msg(mqtt_client, server, base_url, lock, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    ctx = dan.register(
        base_url,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )

    topic = ctx.i_chans['ctrl']
    rev = ctx.rev

    assert ctx.rev is not None
    sleep(1)  # make DA busy
    dan.deregister()

    def on_msg(client, user_data, msg):
        on_msg.topic = msg.topic
        on_msg.payload = json.loads(msg.payload.decode())
        lock.release()

    mqtt_client.on_message = on_msg
    mqtt_client.subscribe(topic)

    lock.acquire()  # wait for message

    assert on_msg.topic == topic
    assert on_msg.payload == {
        'state': 'offline',
        'rev': rev,
    }


def test_on_online_pub(simple_da):
    assert simple_da.mqtt_client.on_publish is None


def test_register_without_name(server, base_url, uuid, dan):
    def on_data(*args):
        pass

    def on_signal(*args):
        pass

    context = dan.register(
        base_url,
        id_=uuid,
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        odf_list=[('meow', ['dB'])],
        profile={
            'model': 'AI',
        },
    )

    assert context.rev is not None

    url = '{}/{}'.format(base_url, uuid)
    res = requests.get(url)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data['id'] == uuid
    assert data.get('name') is not None


# if the playload is not a dict or list,
# wrap it into list then encode to json
@pytest.mark.parametrize('payload', [42, "string", None])
def test_push(dan, simple_da, payload):
    def pub(topic, data, **kwargs):
        '''
        mock publish function
        '''
        assert topic == 'magic'
        assert data == json.dumps([payload])

    simple_da.i_chans['meow'] = 'magic'
    orig_pub = simple_da.mqtt_client.publish
    simple_da.mqtt_client.publish = pub

    dan.push('magic', payload)

    simple_da.mqtt_client.publish = orig_pub


@pytest.mark.parametrize('payload', [
    (-4, 3),
    [3, -4],
    {'answer': 42},
])
def test_push_json(dan, simple_da, payload):
    def pub(topic, data, **kwargs):
        '''
        mock publish function
        '''
        assert topic == 'magic'
        assert data == json.dumps(payload)

    simple_da.i_chans['meow'] = 'magic'
    orig_pub = simple_da.mqtt_client.publish
    simple_da.mqtt_client.publish = pub

    dan.push('magic', payload)

    simple_da.mqtt_client.publish = orig_pub
