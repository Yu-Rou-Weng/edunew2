'''
.. todo::

    - integration test for control message. Maybe we need a testing device
      application.
'''
import pytest

from uuid import uuid4

from iot.csm.ctrl import connect, disconnect


@pytest.fixture(params=('CONNECT', 'DISCONNECT'))
def connection_cmd(request):
    return request.param


@pytest.fixture(params=('idf', 'odf'))
def mode(request):
    return request.param


@pytest.fixture()
def msg_id():
    return str(uuid4())


@pytest.fixture()
def connect_msg(request, msg_id, topic, connection_cmd, mode):
    return {
        'msg_id': msg_id,
        mode: 'meow',
        'command': connection_cmd,
        'topic': topic,
    }


def test_connect_disconnect(connect_msg, msg_id, topic, connection_cmd, mode):
    def mock_pub(payload):
        assert payload == connect_msg

    if connection_cmd == 'CONNECT':
        connect(msg_id=msg_id, mode=mode, feature='meow', topic=topic,
                pub=mock_pub)
    elif connection_cmd == 'DISCONNECT':
        disconnect(msg_id=msg_id, mode=mode, feature='meow', topic=topic,
                   pub=mock_pub)
