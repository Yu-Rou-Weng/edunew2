import pytest

from hashlib import sha256

import zmq

from iot.csm.storage import Link, UserFunction


@pytest.fixture()
def _link():
    assert Link.clear()
    assert Link.select() == {}
    yield
    assert Link.clear()
    assert Link.select() == {}


@pytest.fixture()
def _func():
    assert UserFunction.clear()
    assert UserFunction.select() == {}
    yield
    assert UserFunction.clear()
    assert UserFunction.select() == {}


def test_link_add_set(_link):
    args = ('id', 'feature', 'idf', 'graph1')
    assert Link.add(*args) == (1, Link.PENDING)
    assert Link.select() == {('id', 'feature', 'idf'): Link.PENDING}

    args = ('id', 'feature', 'idf', 'topic')
    assert Link.set(*args) is True
    assert Link.select() == {('id', 'feature', 'idf'): 'topic'}


def test_link_add_conflict(_link):
    args = ('id', 'feature', 'idf', 'graph1')
    assert Link.add(*args) == (1, Link.PENDING)
    assert Link.select() == {('id', 'feature', 'idf'): Link.PENDING}

    with pytest.raises(ValueError) as err:
        Link.add(*args)

    assert 'exists' in str(err)


def test_link_add_diff_graph(_link):
    args = ('id', 'feature', 'idf', 'graph1')
    assert Link.add(*args) == (1, Link.PENDING)
    assert Link.select() == {('id', 'feature', 'idf'): Link.PENDING}

    args = ('id', 'feature', 'idf', 'graph2')
    assert Link.add(*args) == (2, Link.PENDING)
    assert Link.select() == {('id', 'feature', 'idf'): Link.PENDING}


def test_link_set_not_exist(_link):
    args = ('id', 'feature', 'idf', 'topic')

    with pytest.raises(ValueError) as err:
        Link.set(*args)

    assert 'not exist' in str(err)


def test_link_set_conflict(_link):
    args = ('id', 'feature', 'idf', 'graph1')
    assert Link.add(*args) == (1, Link.PENDING)
    args = ('id', 'feature', 'idf', 'topic')
    assert Link.set(*args) is True
    assert Link.select() == {('id', 'feature', 'idf'): 'topic'}

    with pytest.raises(ValueError) as err:
        Link.set(*args)

    assert 'already sets' in str(err)


def test_link_rm(_link):
    assert Link.add('id', 'feature', 'idf', 'graph1') == (1, Link.PENDING)
    assert Link.rm('id', 'feature', 'idf', 'graph1') == 0


def test_link_rm_none(_link):
    with pytest.raises(ValueError) as err:
        Link.rm('id', 'feature', 'idf', 'graph1')

    assert 'unknown' in str(err)


def test_rm_wrong_graph_id(_link):
    assert Link.add('id', 'feature', 'idf', 'graph1') == (1, Link.PENDING)

    with pytest.raises(ValueError) as err:
        Link.rm('id', 'feature', 'idf', 'graph2')

    assert 'unknown' in str(err)


def test_link_select_key(_link):
    assert Link.add('id', 'feature', 'idf', 'graph1')
    assert Link.select('id', 'feature', 'idf', 'graph1') == Link.PENDING
    assert Link.select('id', 'feature', 'idf') == (1, Link.PENDING)
    assert Link.select('id', 'feature', 'idf', 'graph2') is None
    assert Link.select('id', 'feature', 'meow', 'graph1') is None


def test_link_unknown_cmd(_link):

    class Foo(Link):
        @staticmethod
        def answer():
            req = zmq.Context.instance().socket(zmq.REQ)
            req.connect('inproc://link')
            req.send_pyobj(('answer', 42))
            return req.recv_pyobj()

    # the io thread should not crash or hang
    assert Foo.answer() is False


def test_function_add(_func):
    src = (
        'def run():\n'
        '    pass'
    )
    key = sha256(src.encode('utf-8')).hexdigest()

    assert UserFunction.add(key, src)
    assert UserFunction.select(key) == src


def test_function_add_key_mismatch(_func):
    src = (
        'def run():\n'
        '    pass'
    )

    with pytest.raises(ValueError) as err:
        assert UserFunction.add('42', src)

    assert UserFunction.select() == {}
    assert 'mismatched' in str(err)


def test_function_add_duplicate(_func):
    src = (
        'def run():\n'
        '    pass'
    )
    key = sha256(src.encode('utf-8')).hexdigest()

    assert UserFunction.add(key, src)
    assert UserFunction.select(key) == src

    assert UserFunction.add(key, src) is False


def test_function_rm(_func):
    src = (
        'def run():\n'
        '    pass'
    )
    key = sha256(src.encode('utf-8')).hexdigest()

    assert UserFunction.add(key, src)
    assert UserFunction.select(key) == src

    assert UserFunction.rm(key)
    assert UserFunction.select() == {}


def test_function_rm_unknown(_func):
    assert UserFunction.rm('magic') is False


def test_function_select_unknown(_func):
    assert UserFunction.select('magic') is None
