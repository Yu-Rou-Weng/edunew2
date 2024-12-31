import pytest

from functools import partial
from uuid import uuid4

from paho.mqtt import client as mqtt

from iot.config import config
from iot.conn import Conn, ConnMap, CtrlConn, DevAppState, DataConnMap, IoTConnMgr


@pytest.fixture
def iot_conn_mgr():
    conf = config.mqtt_conf
    i = IoTConnMgr(auto_connect=False)
    i.setup_conn('mqtt', conf['host'], port=conf['port'], client_id=uuid4())

    assert i.mqtt_c
    assert i.mqtt_connected
    yield i


def test_IoTConnMgr_setup_invalid(iot_conn_mgr):
    with pytest.raises(NotImplementedError) as err:
        iot_conn_mgr.setup_conn('magic')

    assert 'Protocol' in str(err)
    assert 'not supported' in str(err)


def test_IotConnMgr_setup_mqtt(iot_conn_mgr):
    iot_conn_mgr.setup_conn('mqtt', 'localhost', port=1883)

    assert isinstance(iot_conn_mgr.mqtt_c, mqtt.Client)
    assert iot_conn_mgr.mqtt_connected


def test_DataConnMap_get_invalid_key():
    d = DataConnMap()
    assert d.get(42) is None


def test_ConnMap_get_invalid_key():
    d = ConnMap()
    assert d.get(42) is None


def test_ConnMap(uuid_obj):
    d = ConnMap()
    assert isinstance(d[uuid_obj], Conn)


def test_ConnMap_get(uuid_obj):
    d = ConnMap()
    assert isinstance(d.get(uuid_obj), Conn)
    assert isinstance(d.get(uuid_obj), Conn)


def test_ConnMap_getitem_invalid_type():
    d = ConnMap()
    with pytest.raises(TypeError):
        d[42]


def test_IoTConnMgr_mqtt_pub_sub(iot_conn_mgr, uuid_obj):
    @iot_conn_mgr.mqtt_sub(uuid_obj, 'meow', '_magic')
    def subscribe_callback(client, userdata, msg):
        assert int(msg.payload) == 42

    pub = iot_conn_mgr.mqtt_pub(uuid_obj, 'meow', '_magic')
    pub(42)

    assert iot_conn_mgr.conns[uuid_obj].data['meow'].i
    assert iot_conn_mgr.conns[uuid_obj].data['meow'].o is pub
    assert isinstance(iot_conn_mgr.conns[uuid_obj].ctrl, CtrlConn)
    assert iot_conn_mgr.conns[uuid_obj].ctrl.pub is None
    assert iot_conn_mgr.conns[uuid_obj].ctrl.sub is None


def test_IoTConnMgr_mqtt_sub_resubscribe(iot_conn_mgr, uuid_obj, topic):
    sub = iot_conn_mgr.mqtt_sub(uuid_obj, 'meow', topic)

    @sub
    def orig_sub():
        pass
    assert iot_conn_mgr.conns[uuid_obj].data['meow'].i.cb is orig_sub

    @sub
    def new_sub():
        pass
    assert iot_conn_mgr.conns[uuid_obj].data['meow'].i.cb is new_sub


def test_IoTConnMgr_ctrl_pub(iot_conn_mgr, uuid_obj):
    pub = iot_conn_mgr.mqtt_pub(uuid_obj, '_ctrl', '_magic')
    assert iot_conn_mgr.conns[uuid_obj].ctrl.pub is pub


def test_IoTConnMgr_ctrl_sub(iot_conn_mgr, uuid_obj):
    sub = iot_conn_mgr.mqtt_sub(uuid_obj, '_ctrl', '_magic')
    assert iot_conn_mgr.conns[uuid_obj].ctrl.sub is sub


def test_IoTConnMgr_sub_return(iot_conn_mgr, uuid_obj):
    @iot_conn_mgr.mqtt_sub(uuid_obj, 'meow', '_magic')
    def on_message(client, userdata, msg):
        return

    func = iot_conn_mgr.conns[uuid_obj].data['meow'].i
    assert func is not None
    assert func.cb is on_message
    assert func.client is iot_conn_mgr.mqtt_c
    assert func.feature == 'meow'
    assert func.id == uuid_obj
    assert func.remove_callback
    assert func.topic == '_magic'


def test_IoTConnMgr_mqtt_ctrl(iot_conn_mgr, uuid_obj):
    pub, sub = iot_conn_mgr.mqtt_ctrl(
        uuid_obj, '_magic/ctrl/o', '_magic_id/ctrl/i', '_rev')
    assert pub is iot_conn_mgr.conns[uuid_obj].ctrl.pub
    assert sub is iot_conn_mgr.conns[uuid_obj].ctrl.sub
    assert '_rev' == iot_conn_mgr.conns[uuid_obj].ctrl.rev


def test_CtrlConn_on_message_online(
        mqtt_client, lock, topic, resource, uuid_obj):
    def lock_wrapper(func):
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            lock.release()
            return ret

        return wrapper

    def sub(func):
        mqtt_client.on_message = lock_wrapper(func)
        return func

    sub.remove_callback = partial(mqtt_client.message_callback_remove, topic)

    rev = str(resource.revision)

    mqtt_client.subscribe(topic)
    ctrl = CtrlConn(uuid_obj, sub=sub, rev=rev)
    mqtt_client.publish(topic, '{"state": "online", "rev": "%s"}' % rev)

    lock.acquire()
    assert ctrl.da_state == DevAppState.ONLINE


def test_CtrlConn_on_message_offline(
        mqtt_client, lock, topic, resource, uuid_obj, httpserver):
    def lock_wrapper(func):
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            lock.release()
            return ret

        return wrapper

    def sub(func):
        mqtt_client.on_message = lock_wrapper(func)
        return func

    sub.remove_callback = partial(mqtt_client.message_callback_remove, topic)
    (httpserver.expect_oneshot_request('/{}'.format(uuid_obj), 'DELETE')
               .respond_with_json({}))
    config.http_port = httpserver.port

    rev = str(resource.revision)

    mqtt_client.subscribe(topic)
    ctrl = CtrlConn(uuid_obj, sub=sub, rev=rev)
    ctrl.da_state = DevAppState.ONLINE
    mqtt_client.publish(topic, '{"state": "offline", "rev": "%s"}' % rev)

    lock.acquire()
    assert ctrl.da_state == DevAppState.OFFLINE


def test_CtrlConn_on_message_cmd_response(mqtt_client, lock, topic, uuid_obj):
    def lock_wrapper(func):
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            lock.release()
            return ret

        return wrapper

    def sub(func):
        mqtt_client.on_message = lock_wrapper(func)
        return func

    sub.remove_callback = partial(mqtt_client.message_callback_remove, topic)

    mqtt_client.subscribe(topic)
    ctrl = CtrlConn(uuid_obj, sub=sub)
    ctrl.da_state = DevAppState.ONLINE
    mqtt_client.publish(topic, '{"state": "ok", "msg_id": "magic"}')

    lock.acquire()
