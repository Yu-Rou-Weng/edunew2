import pytest

from time import sleep
from uuid import uuid4

from iot.esm import worker
from iot.esm.worker import CompilationError, Worker, _Conf


@pytest.fixture()
def simple_func():
    return 'def run(x): return x'


@pytest.fixture()
def idf_conf():
    return {
        'id': ('da_id', 'feature'),
        'src': 'def run(x): return x\n',
        'topic': 'iottalk/test/i'
    }


@pytest.fixture()
def odf_conf():
    return {
        'id': ('da_id', 'feature'),
        'src': 'def run(x): return x\n',
        'topic': 'iottalk/test/o'
    }


def test_compile_none():
    assert worker._compile(None) == (None, None, None)


def test_compile():
    src = 'def run(x): return int(x)\n'
    dgt = 'f87d5c678bdd9e4b1b5f278c29cdf9a0fd01198060d8c6f3a34a6a05ae536e50'

    func, context, digest = worker._compile(src)

    assert context['run'] is func
    assert func('42') == 42
    assert digest == dgt


def test_func_not_found():
    src = 'answer = 42\n'

    with pytest.raises(CompilationError) as err:
        worker._compile(src)

    assert 'not found' in str(err)


def test_compile_wrong_type():
    src = 'run = 42\n'

    with pytest.raises(CompilationError) as err:
        worker._compile(src)

    assert 'must be a function' in str(err)


def test_compile_fail():
    src = 'answer\n'

    with pytest.raises(CompilationError) as err:
        worker._compile(src)

    assert 'Traceback' in str(err)


def test_compile_context():
    src = (
        'answer = 42\n'
        'def run(x):\n'
        '  pass\n'
    )
    dgt = '94def1cec78a35ef376028f63cff12b6b7f1b14f9dbfde104c3e592cda8145f9'

    func, context, digest = worker._compile(src)

    assert context['answer'] == 42
    assert digest == dgt


def test_idf_confs_setter():
    w = Worker(None, None, None, uuid4())

    assert w.idf_confs == []

    w.idf_confs = [{
        'id': ('da_id', 'feature'),
        'src': None,
        'topic': 'test',
    }]

    assert w.idf_confs == [{
        'id': ('da_id', 'feature'),
        'src': None,
        'digest': None,
        'topic': 'test',
    }]


def test_odf_confs_setter():
    w = Worker(None, None, None, uuid4())

    assert w.odf_confs == []

    w.odf_confs = [{
        'id': ('da_id', 'feature'),
        'src': None,
        'topic': 'test',
    }]

    assert w.odf_confs == [{
        'id': ('da_id', 'feature'),
        'src': None,
        'digest': None,
        'topic': 'test',
    }]


@pytest.mark.parametrize('df', ['idf', 'odf'])
def test_df_confs_setter_deps(func_foo, df):
    foo, sig = func_foo
    w = Worker(None, None, None, uuid4())
    attr = '{df}_confs'.format(df=df)

    assert getattr(w, attr) == []

    setattr(w, attr, [{
        'id': ('da_id', 'feature'),
        'src': None,
        'topic': 'test',
        'deps': [(foo, 'foo')],
    }])

    c = getattr(w, attr)[0]
    assert set(c.keys()) == set(
        ['id', 'src', 'topic', 'digest', 'deps_src'])


def test_join_func_setter():
    w = Worker(None, None, None, uuid4())

    assert w.join_func == {'src': None}

    w.join_func = 'def run(): pass\n'

    assert w.join_func['src'] == 'def run(): pass\n'
    assert w.join_func['digest']


def test_worker_init_none():
    w = Worker(graph_id=uuid4())

    assert w.idf_confs == []
    assert w.odf_confs == []
    assert w.join_func == {'src': None}
    assert w.start() is False


def test_worker_init_idf_only(idf_conf):
    w = Worker([idf_conf], graph_id=uuid4())

    assert w.odf_confs == []
    assert w.join_func == {'src': None}
    conf = w.idf_confs[0]
    assert conf.get('id') == idf_conf['id']
    assert conf.get('src') == idf_conf['src']
    assert conf.get('topic') == idf_conf['topic']
    assert conf.get('digest')

    assert w.start()
    sleep(1)
    w.stop()


def test_worker_init_odf_only(odf_conf):
    w = Worker(odf_confs=[odf_conf], graph_id=uuid4())

    assert w.idf_confs == []
    assert w.join_func == {'src': None}
    conf = w.odf_confs[0]
    assert conf.get('id') == odf_conf['id']
    assert conf.get('src') == odf_conf['src']
    assert conf.get('topic') == odf_conf['topic']
    assert conf.get('digest')

    assert w.start() is False
    sleep(1)
    w.stop()


def test_worker_init_join_only():
    src = 'def run(x): return x\n'
    w = Worker(join_func=src, graph_id=uuid4())

    assert w.idf_confs == []
    assert w.odf_confs == []
    assert w.join_func.get('src') == src
    assert w.join_func.get('digest')

    assert w.start() is False


def test_worker_restart(idf_conf):
    w = Worker([idf_conf], graph_id=uuid4())

    assert w.start()
    proc = w._proc
    sleep(1)
    assert w.start()  # restart
    assert proc is not w._proc
    w.stop()


def test_Conf_init():
    conf = {
        'src': 'def run(x): return x\n',
    }
    c = _Conf(conf)

    assert c['src'] == 'def run(x): return x\n'
    assert c.get('digest')


def test_Conf_init_empty():
    c = _Conf({})
    assert c == {}


def test_Conf_setitem():
    c = _Conf({})

    c['foo'] = 'bar'
    assert c.get('foo') == 'bar'
    assert c.get('func') is None
    assert c.get('digest') is None

    c['src'] = 'def run(x): return x\n'
    assert c.get('digest')


def test_Conf_reinit():
    c = _Conf(_Conf({'foo': 'bar'}))

    assert not isinstance(c.data, _Conf)
    assert c['foo'] == 'bar'


def test_Conf_compile_dep(func_foo):
    src, sig = func_foo

    dep = _Conf._compile_dep(src, 'foo')
    assert set(dep.keys()) == set(['src', 'digest', 'alias', 'func'])
    assert dep['func']
    assert dep['src'] == src
    assert dep['digest'] == sig
    assert dep['alias'] == 'foo'


def test_Conf_compile_deps(func_foo, func_bar):
    foo, fsig = func_foo
    bar, bsig = func_bar

    deps = _Conf._compile_deps([(foo, 'foo'),
                                (bar, 'bar')])

    for dep in deps:
        assert set(dep.keys()) == set(['src', 'digest', 'alias', 'func'])
        assert dep['func']

    assert deps[0]['src'] == foo
    assert deps[0]['digest'] == fsig
    assert deps[0]['alias'] == 'foo'

    assert deps[1]['src'] == bar
    assert deps[1]['digest'] == bsig
    assert deps[1]['alias'] == 'bar'


def test_Conf_iot_deps_context(func_foo, func_bar):
    foo, fsig = func_foo
    bar, bsig = func_bar

    deps = _Conf._compile_deps([(foo, 'foo'),
                                (bar, 'bar')])
    iot = _Conf._iot_deps_context(deps)

    assert iot.foo is deps[0].get('func')
    assert iot.bar is deps[1].get('func')


def test_add_idf_conf(simple_func):
    w = Worker(graph_id=uuid4())

    assert len(w.idf_confs) == 0
    w.add_idf_conf({
        'id': ('magic', 'rng'),
        'src': simple_func,
    })
    assert len(w.idf_confs) == 1

    conf = w.idf_confs[-1]
    assert conf['src'] == simple_func
    assert conf['digest']


def test_add_odf_conf(simple_func):
    w = Worker(graph_id=uuid4())

    assert len(w.odf_confs) == 0
    w.add_odf_conf({
        'id': ('magic', 'rng'),
        'src': simple_func,
    })
    assert len(w.odf_confs) == 1

    conf = w.odf_confs[-1]
    assert conf['src'] == simple_func
    assert conf['digest']


def test_rm_idf_conf(idf_conf):
    w = Worker(idf_confs=[idf_conf], graph_id=uuid4())
    assert len(w.idf_confs) == 1
    w.rm_conf(('da_id', 'feature'), 'idf')
    assert len(w.idf_confs) == 0


def test_rm_idf_conf_unknown(idf_conf):
    w = Worker(idf_confs=[idf_conf], graph_id=uuid4())
    assert len(w.idf_confs) == 1
    w.rm_conf(('?', '??'), 'idf')
    assert len(w.idf_confs) == 1


def test_rm_odf_conf(odf_conf):
    w = Worker(odf_confs=[odf_conf], graph_id=uuid4())
    assert len(w.odf_confs) == 1
    w.rm_conf(('da_id', 'feature'), 'odf')
    assert len(w.odf_confs) == 0


def test_rm_non_existing_odf_conf(odf_conf):
    w = Worker(odf_confs=[odf_conf], graph_id=uuid4())
    assert len(w.odf_confs) == 1
    w.rm_conf(('?', '?'), 'odf')
    assert len(w.odf_confs) == 1


def test_get_idf_conf(idf_conf):
    w = Worker(idf_confs=[idf_conf], graph_id=uuid4())

    conf = w.get_idf_conf('da_id', 'feature')
    assert isinstance(conf, _Conf)
    assert conf['id'] == idf_conf['id']
    assert conf['src'] == idf_conf['src']
    assert conf['topic'] == idf_conf['topic']


def test_get_odf_conf(odf_conf):
    w = Worker(odf_confs=[odf_conf], graph_id=uuid4())

    conf = w.get_odf_conf('da_id', 'feature')
    assert isinstance(conf, _Conf)
    assert conf['id'] == odf_conf['id']
    assert conf['src'] == odf_conf['src']
    assert conf['topic'] == odf_conf['topic']


def test_get_idf_conf_via_add(idf_conf):
    w = Worker(graph_id=uuid4())
    w.add_idf_conf(idf_conf)

    conf = w.get_idf_conf('da_id', 'feature')
    assert isinstance(conf, _Conf)
    assert conf['id'] == idf_conf['id']
    assert conf['src'] == idf_conf['src']
    assert conf['topic'] == idf_conf['topic']


def test_get_odf_conf_via_add(odf_conf):
    w = Worker(graph_id=uuid4())
    w.add_odf_conf(odf_conf)

    conf = w.get_odf_conf('da_id', 'feature')
    assert isinstance(conf, _Conf)
    assert conf['id'] == odf_conf['id']
    assert conf['src'] == odf_conf['src']
    assert conf['topic'] == odf_conf['topic']
