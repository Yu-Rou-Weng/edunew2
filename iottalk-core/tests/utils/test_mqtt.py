# FIXME: this file should be placed in ``iottalk-utils``
import pytest

from json import JSONDecodeError
from mock import Mock

from iotutils.mqtt import JsonClient, mqtt_json_payload, mqtt_json_pub


def test_mqtt_json_payload():
    @mqtt_json_payload
    def on_msg(client, userdata, msg):
        assert msg.payload == {'answer': 42}

    msg = Mock()
    msg.payload = b'{"answer": 42}'
    on_msg(None, None, msg)


def test_integration_mqtt_json_payload(mqtt_client, lock, topic):
    @mqtt_json_payload
    def on_msg(client, userdata, msg):
        on_msg.ret = msg.payload
        userdata.release()

    on_msg.ret = None

    mqtt_client.on_message = on_msg
    mqtt_client.publish(topic, '{"answer": 42}')

    lock.acquire()
    assert on_msg.ret == {'answer': 42}


def test_mqtt_json_class_method(mqtt_client, lock, topic):
    class C(object):
        @mqtt_json_payload
        def f(self, client, userdata, msg):
            self.msg = msg
            userdata.release()

    c = C()
    mqtt_client.on_message = c.f
    mqtt_client.publish(topic, '{"answer": 42}')

    lock.acquire()
    assert c.msg.topic == topic
    assert c.msg.payload == {'answer': 42}


def test_mqtt_json_payload_dectorator_factory():
    @mqtt_json_payload()
    def on_msg(client, userdata, msg):
        assert msg.payload == {'answer': 42}

    msg = Mock()
    msg.payload = b'{"answer": 42}'
    on_msg(None, None, msg)


def test_mqtt_json_payload_type_error():
    @mqtt_json_payload
    def on_msg(client, userdata, msg):
        pass

    msg = Mock()
    msg.payload = b'42'

    with pytest.raises(TypeError):
        on_msg(None, None, msg)


def test_mqtt_json_payload_decode_fail():
    @mqtt_json_payload
    def on_msg(client, userdata, msg):
        pass

    msg = Mock()
    msg.payload = b'answer'

    with pytest.raises(JSONDecodeError):
        on_msg(None, None, msg)


def test_mqtt_json_payload_fail_no_raise():
    @mqtt_json_payload(raise_error=False)
    def on_msg(client, userdata, msg):
        assert False  # should not be ran

    msg = Mock()
    msg.payload = b'42'

    on_msg(None, None, msg)


def test_mqtt_json_pub(mqtt_client, lock, topic):
    def on_msg(client, userdata, msg):
        on_msg.msg = msg
        userdata.release()

    on_msg.msg = None

    mqtt_client.on_message = on_msg
    pub = mqtt_json_pub(mqtt_client.publish)
    pub(topic, {'answer': 42})

    lock.acquire()
    assert on_msg.msg.payload == b'{"answer": 42}'


def test_mqtt_json_pub_invalid_type(mqtt_client, topic):
    pub = mqtt_json_pub(mqtt_client.publish)

    with pytest.raises(TypeError):
        pub(topic, 42)

    with pytest.raises(TypeError):
        pub(topic, 'magic')


def test_mqtt_json_pub_encode_error(mqtt_client, topic):
    pub = mqtt_json_pub(mqtt_client.publish)

    with pytest.raises(TypeError):
        pub(topic, [Mock()])


def test_mqtt_json_pub_dectorator_factory(topic):
    @mqtt_json_pub()
    def f(*args, **kwargs):
        assert args[0] == topic
        assert args[1] == '[42]'

    f(topic, [42])


def test_mqtt_json_pub_no_raise(topic):
    @mqtt_json_pub(raise_error=False)
    def f(*args, **kwargs):
        assert False  # should no be executed

    f(topic, 42)


def test_JsonClient_pub_sub(lock, topic):
    def on_message(client, userdata, msg):
        on_message.msg = msg
        userdata.release()

    on_message.msg = None

    # setup
    c = JsonClient(userdata=lock)
    c.connect('localhost')
    c.subscribe(topic)

    c.on_json_message = on_message
    c.publish_json(topic, {'answer': 42})

    c.loop_start()

    lock.acquire()

    assert c.on_json_message
    assert on_message.msg.topic == topic
    assert on_message.msg.payload == {'answer': 42}

    # teardown
    c.disconnect()
    c.loop_stop()
