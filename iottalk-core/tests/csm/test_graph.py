import pytest

from uuid import uuid4

from iot.csm.graph import Graph
from iot.csm.storage import UserFunction


@pytest.fixture()
def _func():
    assert UserFunction.clear()
    assert UserFunction.select() == {}
    yield
    assert UserFunction.clear()
    assert UserFunction.select() == {}


@pytest.fixture()
def _req():
    def f(callback):
        pass
    return f


@pytest.fixture()
def _res():
    def f(payload):
        return payload
    f.remove_callback = (lambda: None)
    return f


@pytest.fixture()
def graph(_req, _res):
    g = Graph(_req, _res, id_=uuid4())
    yield g


@pytest.fixture()
def _add_funcs(graph, func_foo, func_bar):
    foo_src, foo_sig = func_foo
    bar_src, bar_sig = func_bar

    graph.op_add_funcs({
        'op': 'add_funcs',
        'codes': [foo_src, bar_src],
        'digests': [foo_sig, bar_sig],
    })

    assert UserFunction.select() == {
        foo_sig: foo_src,
        bar_sig: bar_src,
    }
    yield


def test_response_func_success(graph):
    def success(payload):
        return payload

    def error(payload):
        assert False

    req_payload = {
        'op': 'add_link',
        'odf': 'meow',
    }

    res_payload = {
        'msg_id': 'magic',
        'state': 'ok'
    }

    success, error = graph.response_func(req_payload, success, error)

    res = success(res_payload)

    # the ``msg_id`` should not be reveal to api client
    assert 'msg_id' not in res
    assert res == {
        'op': 'add_link',
        'odf': 'meow',
        'state': 'ok'}


def test_response_func_error(graph):
    def success(payload):
        assert False

    def error(payload):
        return payload

    req_payload = {
        'op': 'add_link',
        'odf': 'meow',
    }

    res_payload = {
        'msg_id': 'magic',
        'state': 'error',
        'reason': 'foo'
    }

    success, error = graph.response_func(req_payload, success, error)

    res = error(res_payload)

    # the ``msg_id`` should not be reveal to api client
    assert 'msg_id' not in res
    assert res == {
        'op': 'add_link',
        'odf': 'meow',
        'state': 'error',
        'reason': 'foo'}


def test_response_func_none(graph):
    req_payload = {
        'op': 'add_link',
        'odf': 'meow',
    }

    res_payload = {
        'msg_id': 'magic',
        'state': 'error',
        'reason': 'foo'
    }

    success, error = graph.response_func(
        req_payload, on_success=None, on_error=None)

    res = success(res_payload)

    # the ``msg_id`` should not be reveal to api client
    assert 'msg_id' not in res
    assert res == {
        'op': 'add_link',
        'odf': 'meow',
        'state': 'error',
        'reason': 'foo'}


def test_get_mode(graph):
    d = {
        'op': 'magic',
        'odf': 'meow',
    }

    assert graph.get_mode(d.keys()) == 'odf'


def test_get_mode_duplicate(graph):
    d = {
        'op': 'magic',
        'odf': 'meow',
        'idf': 'meow',
    }

    with pytest.raises(ValueError) as err:
        graph.get_mode(d.keys())

    assert 'duplicated' in str(err)


def test_get_mode_miss(graph):
    d = {
        'op': 'magic',
    }

    with pytest.raises(ValueError) as err:
        graph.get_mode(d.keys())

    assert 'not found' in str(err)


def test_op_add_funcs_single(graph, _func):
    func_src = 'def f(): pass'
    func_sig = (
        '3c70e0681767dfd372b5fd92795a22c070937db46671cac5140bbbc5ffa552b3')

    payload = {
        'op': 'add_funcs',
        'codes': [func_src],
        'digests': [func_sig],
    }

    graph.op_add_funcs(payload)

    assert UserFunction.select() == {func_sig: func_src}


def test_op_add_funcs_multi(graph, _func):
    foo_src = 'def foo(): pass'
    bar_src = 'def bar(): pass'
    foo_sig = (
        'edd9f8855bc0387c75b6cd52ba6cadbaf706d0cecade3445832374978ee01dcd')
    bar_sig = (
        'a7b41e562e909c378b102162c118bf83cfa30fc06908436b8ba3cc99aaf42575')

    graph.op_add_funcs({
        'op': 'add_funcs',
        'codes': [foo_src, bar_src],
        'digests': [foo_sig, bar_sig],
    })

    assert UserFunction.select() == {
        foo_sig: foo_src,
        bar_sig: bar_src,
    }


def test_op_rm_funcs_single(graph, _func):
    func_src = 'def f(): pass'
    func_sig = (
        '3c70e0681767dfd372b5fd92795a22c070937db46671cac5140bbbc5ffa552b3')

    payload = {
        'op': 'add_funcs',
        'codes': [func_src],
        'digests': [func_sig],
    }

    graph.op_add_funcs(payload)

    assert UserFunction.select() == {func_sig: func_src}

    graph.op_rm_funcs({
        'op': 'rm_funcs',
        'codes': [func_src],
        'digests': [func_sig],
    })

    assert UserFunction.select() == {}


def test_op_rm_funcs_multi(graph, _func, _add_funcs, func_foo, func_bar):
    foo_src, foo_sig = func_foo
    bar_src, bar_sig = func_bar

    graph.op_rm_funcs({
        'op': 'rm_funcs',
        'digests': [foo_sig],
    })

    assert UserFunction.select() == {bar_sig: bar_src}


def test_op_set_join(graph, _func, _add_funcs, func_foo):
    _, foo_sig = func_foo

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': foo_sig,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'ok'
    assert res['new'] == foo_sig


def test_op_set_join_null(graph, _func):
    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': None,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'ok'


def test_op_set_join_non_exit(graph, _func):
    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': 'magic',
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'error'
    assert 'reason' in res
    assert 'not found' in res['reason'], res['reason']


def test_op_set_join_change(graph, _func, _add_funcs, func_foo, func_bar):
    _, foo_sig = func_foo
    _, bar_sig = func_bar

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': foo_sig,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'ok'
    assert res['new'] == foo_sig

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': foo_sig,
        'new': bar_sig,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'ok', res['reason']
    assert res['new'] == bar_sig


def test_op_set_join_prev_mismatch(graph, _func, _add_funcs,
                                   func_foo, func_bar):
    _, foo_sig = func_foo
    _, bar_sig = func_bar

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': 'magic',
        'new': foo_sig,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'error'
    assert 'reason' in res
    assert 'mismatch' in res['reason']


def test_op_set_join_prev_mismatch2(graph, _func, _add_funcs,
                                    func_foo, func_bar):
    _, foo_sig = func_foo
    _, bar_sig = func_bar

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': foo_sig,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'ok', res['reason']
    assert res['new'] == foo_sig

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': foo_sig + '!',
        'new': bar_sig,
    })

    assert res['op'] == 'set_join'
    assert res['state'] == 'error'
    assert 'reason' in res
    assert 'mismatch' in res['reason']


def test_op_set_join_deps_unknown(graph, _func, _add_funcs, func_foo):
    src, sig = func_foo

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': sig,
        'depends': {
            'foo': 'magic_hash',
        },
    })

    assert res['state'] == 'error'
    assert 'dependency' in res['reason']
    assert 'unknown' in res['reason']
    assert 'magic_hash' in res['reason']


def test_op_set_join_deps(graph, _func, func_foo, func_bar):
    foo, fsig = func_foo
    bar, bsig = func_bar

    graph.op_add_funcs({
        'op': 'add_funcs',
        'codes': [foo, bar],
        'digests': [fsig, bsig],
    })

    res = graph.op_set_join({
        'op': 'set_join',
        'prev': None,
        'new': fsig,
        'depends': {
            'foo': fsig,
            'bar': bsig,
        },
    })

    assert res['state'] == 'ok'
    assert res['op'] == 'set_join'
    assert res['state'] == 'ok', res['reason']
    assert res['new'] == fsig


def test_unknown_op(graph):
    class msg:
        payload = {
            'op': 'magic_op',
        }

    def res(payload):
        assert payload['state'] == 'error'
        assert payload['op'] == 'magic_op'

        assert 'unknown' in payload['reason']
        assert 'magic_op' in payload['reason']

    graph.res = res
    graph.on_req(None, None, msg)
