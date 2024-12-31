import os

from shutil import rmtree
from tempfile import mkdtemp
from threading import Lock
from uuid import UUID, uuid4

import paho
import pytest

from pony import orm

from iot.config import config
from iot.models import db_init
from iot.utils import load_dev_fixtures


@pytest.fixture()
def uuid():
    return '4623de45-c427-4119-86f4-2712d14b6f21'


@pytest.fixture()
def new_uuid():
    return uuid4()


@pytest.fixture()
def uuid_obj(uuid):
    return UUID(uuid)


@pytest.fixture()
def json_header():
    return {
        'Content-Type': 'application/json',
    }


@pytest.fixture()
def db():
    temp_dir = mkdtemp(prefix='iottalk-')
    temp_db = os.path.join(temp_dir, 'test.db')
    config.db_conf = {
        'type': 'sqlite',
        'url': temp_db,
    }
    db_init()
    load_dev_fixtures(config.db)
    yield config.db
    config.db.disconnect()
    config._Config__db = None
    rmtree(temp_dir, ignore_errors=True)


@pytest.fixture()
def alphacat_id():
    # this uuid is from fixtures/dev-99-resource.json
    return 'a54b5bf9-c39b-4248-b611-80d1ed4a36df'


@pytest.fixture
def topic(new_uuid):
    return 'test/{}'.format(new_uuid)


@pytest.fixture()
def lock():
    '''
    a lock useful for blocking
    '''
    lock = Lock()
    lock.acquire()
    yield lock


@pytest.fixture()
def mqtt_client(lock, topic):
    '''
    A mqtt client with a lock stored in ``userdata`` and a topic subscribed
    '''
    conf = config.mqtt_conf
    c = paho.mqtt.client.Client(userdata=lock)
    c.connect(conf['host'], conf['port'])
    c.subscribe(topic)
    c.loop_start()
    yield c
    c.disconnect()
    c.loop_stop()


@pytest.fixture
def resource(db, new_uuid):
    with orm.db_session:
        res = db.Resource(id=new_uuid)

    yield res


@pytest.fixture()
def func_foo():
    src = 'def run(): "foo"'
    sig = (
        '8211c6b7f22bbdf08f1e5724fdbfc5b29ba55111cd8a80a1203e8656f5194174')
    # via hashlib.sha256(string.encode('utf-8')).hexdigest()
    return src, sig


@pytest.fixture()
def func_bar():
    src = 'def run(): "bar"'
    sig = (
        'ec3aeab5f89b164a71377608e1f88f81b49c3de7e4b6d1da120c4edea2b2e2f1')
    return src, sig
