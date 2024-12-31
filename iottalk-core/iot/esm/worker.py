import json
import logging
import os
import signal
import six
import traceback

from contextlib import suppress
from collections.abc import Iterable
from functools import partial
from hashlib import sha256
from multiprocessing import get_context
from six import StringIO
from six.moves import UserDict
from types import FunctionType
from uuid import uuid4

from paho.mqtt.client import Client

from iot.config import config

log = logging.getLogger('iottalk.esm')
log.setLevel(config.logging_level)


class CompilationError(Exception):
    pass


def _src2digest(src):
    return sha256(src.encode('utf-8')).hexdigest() if src is not None else None


def _compile(src, ctx=None):
    '''
    Compile the function source

    :param src: function source
    :param ctx: context dict object
    :return: (function object, context, digest) tuple
        if ``src`` is ``None``, return ``None, None``.
    :raise CompilationError: if compilation failed.
        if ``run`` is not declared in context.
        if ``run`` not a function.
    '''
    if src is None:
        return None, None, None

    digest = _src2digest(src)
    filename = '<UserFunction:{}>'.format(digest)
    context = ctx if ctx is not None else {}

    try:
        code = compile(src, filename, mode='exec')
        exec(code, context)
    except Exception:
        exc_output = StringIO()
        traceback.print_exc(file=exc_output)
        log.debug('User defined function exception:\n %s',
                  exc_output.getvalue())
        raise CompilationError(exc_output.getvalue())

    func = context.get('run', None)
    if func is None:
        raise CompilationError('`run` not found in {}'.format(filename))
    elif not isinstance(func, FunctionType):
        raise CompilationError('`run` must be a function')
    return func, context, digest


class _Conf(UserDict):
    '''
    Conf object for ``idf_confs``, ``odf_confs`` and ``join_func``

    :type data: dict

    :param data:
        {
            'id': (<da_id>, <feature>),
            'input_type': (['variant' | 'sample'], ...)
            'src': <func_code>,
            'topic': <da_topic>,
            'deps': <other_func_hash>,
        }

    fields after compilation:
    :param src:
    :param func: the function object
    :param deps:
    '''

    def __init__(self, data):
        data = data.data if isinstance(data, _Conf) else data

        # init context and all compilation should share it
        self._ctx = {}

        if six.PY2:
            UserDict.__init__(self, data)
            if data and 'src' in data:  # hack for python2
                self['src'] = data['src']
            elif data and 'deps' in data:
                self['deps'] = data['deps']
        else:
            super().__init__(data)

    def __setitem__(self, key, val):
        """
        Special case:
            - key ``deps``,
              it's val should be ``[(src, alias), (src, alias), ...]``.
        """
        d = self.data

        if key == 'src':
            d['src'] = val
            d['digest'] = _src2digest(val)  # although double generated
        elif key == 'deps' and val is not None:
            d['deps_src'] = val
        else:
            d[key] = val

    def compile(self):
        '''
        Should only run once in the standalone esm process.
        '''
        d = self.data

        for k, v in list(d.items()):
            if k == 'src':
                d['func'], _, d['digest'] = _compile(v, self._ctx)
            elif k == 'deps_src':
                d['deps'] = self._compile_deps(v)
                self._ctx.update({'iot': self._iot_deps_context(d['deps'])})

    @classmethod
    def _compile_deps(self, deps):
        return tuple(self._compile_dep(*dep) for dep in deps)

    @staticmethod
    def _compile_dep(src, alias):
        '''
        :return: a dict of {
            'src': 'def f(): pass',
            'alias': '...',
            'func': func object,
            'digest': 'SHA256',
        }
        '''
        f, _, digest = _compile(src)
        return {
            'src': src,
            'alias': alias,
            'func': f,
            'digest': digest,
        }

    @staticmethod
    def _iot_deps_context(deps):
        '''
        Render the context object of depends
        '''
        class Iot(object):
            pass

        _iot = Iot()
        tuple(setattr(_iot, dep['alias'], dep['func']) for dep in deps)
        log.debug('dependency injection %s', dir(_iot))
        return _iot


class Worker(object):
    '''
    The ESM worker process

    :param idf_confs: list of the configs of input feature device::

            [
                {
                    'id': (str('da_id'), 'feature_name'),
                    'src': 'def run(x): return y\n',
                    'topic': '...',
                    'deps' ((src, alias), (src, alias), ...),  // optional
                },
                {
                    'id': (str('da_id'), 'feature_name'),
                    'src': None,    // for raw data
                    'topic': '...',
                    'deps' ((src, alias), (src, alias), ...),  // optional
                },
                ...
            ]


    :param join_func: the join function source or ``None``.
    :param odf_confs: list of config of input feature.
    :param graph_id: for rendering MQTT client id as ``esm-{graph_id}``.
    '''

    def __init__(self, idf_confs=None, join_func=None,
                 odf_confs=None, graph_id=None):
        self._idf_confs = []
        self._idf_confs_map = {}  # mapping for querying via (da_id, feature)
        self._odf_confs = []
        self._odf_confs_map = {}  # mapping for querying via (da_id, feature)
        self._join_func = {'src': None}

        if idf_confs:
            self.idf_confs = idf_confs
        if odf_confs:
            self.odf_confs = odf_confs
        if join_func:
            self.join_func = join_func

        if graph_id:
            self.graph_id = graph_id
        else:
            raise ValueError('Invalid graph id: {!r}'.format(graph_id))

        self.mp_context = get_context('forkserver')
        self._proc = self.mp_context.Process(target=self._run)
        self._proc.daemon = True

        self.monitor_mode = False
        self.monitor_topic = 'iottalk/monitor/{}'.format(uuid4())

    def __del__(self):
        self.stop()

    @property
    def idf_confs(self):
        return self._idf_confs

    @idf_confs.setter
    def idf_confs(self, val):
        confs = [_Conf(conf) for conf in val]
        self._idf_confs_map = {conf['id']: conf for conf in confs}
        # set after self._idf_confs_map to prvent from partial updating
        self._idf_confs = confs

    @property
    def odf_confs(self):
        return self._odf_confs

    @odf_confs.setter
    def odf_confs(self, val):
        confs = [_Conf(conf) for conf in val]
        self._odf_confs_map = {conf['id']: conf for conf in confs}
        # set after self._odf_confs_map to prvent from partial updating
        self._odf_confs = confs

    @property
    def join_func(self):
        return self._join_func

    @join_func.setter
    def join_func(self, val):
        '''
        :param val: if ``tuple``, it denotes ``(src, deps)``;
            if ``str``, it's *src*.
        '''
        if isinstance(val, tuple):
            conf = {'src': val[0], 'deps': val[1]}
        else:
            conf = {'src': val}

        self._join_func = _Conf(conf)

    def add_idf_conf(self, conf):
        conf = _Conf(conf)
        self._idf_confs_map[conf['id']] = conf
        self._idf_confs.append(conf)

    def rm_idf_conf(self, id):
        if id not in self._idf_confs_map:
            log.warning('try to rm unknown idf_conf: %s', id)
            return

        conf = self._idf_confs_map.pop(id)
        if conf in self._idf_confs:
            self._idf_confs.remove(conf)

    def add_odf_conf(self, conf):
        conf = _Conf(conf)
        self._odf_confs_map[conf['id']] = conf
        self._odf_confs.append(conf)

    def rm_odf_conf(self, id):
        if id not in self._odf_confs_map:
            log.warning('try to rm unknown odf_conf: %s', id)
            return

        conf = self._odf_confs_map.pop(id)
        if conf in self._odf_confs:
            self._odf_confs.remove(conf)

    def rm_conf(self, id, mode):
        if mode == 'idf':
            self.rm_idf_conf(id)
        elif mode == 'odf':
            self.rm_odf_conf(id)

    def get_idf_conf(self, da_id, feature, default=None):
        '''
        Get the config object from ``idf_confs``

        :param da_id: string of uuid
        :param feature: the feature name
        :param default: the default value if non-exists
        '''
        return self._idf_confs_map.get((da_id, feature), default)

    def get_odf_conf(self, da_id, feature, default=None):
        '''
        Get the config object from ``odf_confs``

        :param da_id: string of uuid
        :param feature: the feature name
        :param default: the default value if non-exists
        '''
        return self._odf_confs_map.get((da_id, feature), default)

    def start(self):
        '''
        Start the ESM task processes.

        If one of ``idf_confs`` is still ``None``,
        we will not start the process because of input topic unknown.
        Then, return ``False``.

        If the process is alive, we will try to restart the process.
        '''
        if not self.idf_confs:
            return False

        self.stop()

        if not self.idf_confs:
            return False

        self._proc.start()
        return True

    def stop(self):
        '''
        Stop the ESM processes and create a new one

        :return:
            ``True`` if terminate successfully
            ``False`` if the _proc is not running before.
        '''
        if self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(2)

        if self._proc.is_alive():  # test is_alive again

            # TODO: rewrite this block as ``self._proc.kill()``,
            #       since Python 3.5 Process.kill is not available
            with suppress(Exception):
                os.kill(self._proc._popen.pid, signal.SIGKILL)

            self._proc.join(2)
            if self._proc.is_alive():  # wtf, who can survive from the SIGKILL.
                log.warning('ESM worker become zombie process')

        # create a new Process
        self._proc = self.mp_context.Process(target=self._run)
        self._proc.daemon = True

    @staticmethod
    def _msg_callback(idf, join, odf_confs, input_buf, buf, buf_idx,
                      monitor_mode, monitor_topic):
        '''
        :param idf: the IDF _Conf object.
        :param join: the join funcion configurations or ``None``.
        :param odf_confs: the ODF _Conf object.
        :param buf: the buffer for keeping idf function output
        :param buf_idx: the index for this idf function.
        :param monitor_mode: if true, send every stages data to monitor
        :param monitor_topic: the topic for sending monitor data.
        '''
        def send_mon_error(client, data):
            '''
            emit ESM error to monitor_topic if monitor mode is ON
            with following payload::

                {
                    'op': 'esm_error',
                    'data': {
                        ...
                    }
                }
            '''
            if not monitor_mode:
                return
            payload = {
                'op': 'esm_error',
                'data': data,
            }
            client.publish(monitor_topic, json.dumps(payload), qos=2)

        def wrapper(client, userdata, msg):
            input_msg = json.loads(msg.payload.decode())
            log.debug("on_message input: %s", input_msg)

            if len(input_msg) != (idf['param_no'] + idf['tag_param_no']):
                log.debug("input params mismatch")
                return

            input_data = input_msg[:idf['param_no']]
            input_tag = input_msg[idf['param_no']:]
            # idf_type: variant or sample
            input_types = idf.get('input_type', ['sample'] * len(input_data))

            try:
                _tmp = [
                    new - pre if input_type == 'variant' else new
                    for input_type, pre, new in zip(
                        input_types, input_buf[buf_idx], input_data)
                ]
            except Exception:
                input_buf[buf_idx] = input_data
            else:
                input_buf[buf_idx] = input_data
                input_data = _tmp

            log.debug("idf input_data: %s", input_data)

            # input function
            if idf.get('func'):
                try:
                    buf[buf_idx] = idf.get('func')(*input_data)
                except Exception as e:
                    log.exception('idf function failure: %r', e)
                    send_mon_error(client, {
                        'msg': 'idf function failure:\n{}'.format(e),
                        'src': idf.get('src')})
                    return

                log.debug("idf function output: %s", buf[buf_idx])
            else:
                buf[buf_idx] = input_data

            log.debug("all input: %s", buf)

            # join function
            if join.get('func'):
                _tmp = []
                for value in buf:
                    if isinstance(value, Iterable) and len(value) == 1:
                        _tmp.extend(value)
                    else:
                        _tmp.append(value)

                try:
                    join_out = join.get('func')(*_tmp)
                except Exception as e:
                    log.exception('join function failure: %r', e)
                    send_mon_error(client, {
                        'msg': 'join function failure:\n{}'.format(e),
                        'src': join.get('src')})
                    return
            else:
                if len(buf) == 1:
                    # # if only one input feature, return scalar
                    join_out = buf[buf_idx]
                else:
                    join_out = buf
            log.debug("join function output: %s", join_out)

            # output function
            odf_monitor = []
            for odf in odf_confs:
                if odf.get('func'):
                    try:
                        tmp_out = odf['func'](*join_out)
                    except Exception as e:
                        log.exception('odf function failure:\n%r\n%r',
                                      e, odf['src'])
                        send_mon_error(client, {
                            'msg': 'odf function failure:\n{}'.format(e),
                            'src': odf.get('src')})
                        return
                else:
                    tmp_out = join_out

                odf_out = [None] * (odf['param_no'] + idf['tag_param_no'])
                for i in range(odf['param_no']):
                    odf_out[i] = tmp_out[min(i, len(tmp_out) - 1)]
                for i in range(odf['tag_param_no']):
                    odf_out[i + odf['param_no']] = input_tag[i]
                log.debug("odf function output: %s", odf_out)
                odf['pub'](json.dumps(odf_out))

                odf_monitor.append({
                    'id': odf['id'],
                    'output': odf_out[:odf['param_no']]
                })

            # send monitor data
            if monitor_mode:
                payload = {
                    'op': 'monitor_info',
                    'data': {
                        'idf': {
                            'id': idf.get('id'),
                            'input': input_data,
                            'output': buf[buf_idx]
                        },
                        'join': {
                            'input': buf,
                            'output': join_out
                        },
                        'odf': odf_monitor,
                    }
                }
                client.publish(monitor_topic, json.dumps(payload), qos=2)

        return wrapper

    def _run(self):
        '''
        The main function of this task.
        '''
        # misc setup
        from iot.cli import main as cli_main
        cli_main(init_only=True)
        logging.raiseExceptions = False

        # compile phase
        [c.compile() for c in self.idf_confs]
        if isinstance(self.join_func, _Conf):
            self.join_func.compile()
        [c.compile() for c in self.odf_confs]

        # join function input buffer, it's a shared memory
        input_buf = [None] * len(self.idf_confs)  # buffer of timeindex
        join_buf = [None] * len(self.idf_confs)  # shared buffer

        def on_connect(client, userdata, flag, rc):
            log.info('ESM %s connect to mqtt broker with return code %s',
                     getattr(client, '_client_id', None), rc)

            # create odf publish partial function
            for conf in self.odf_confs:
                conf['pub'] = partial(client.publish, conf['topic'], qos=2)

            for idx, idf in enumerate(self.idf_confs):
                topic = idf['topic']
                client.subscribe(topic, qos=2)
                client.message_callback_add(
                    topic,
                    self._msg_callback(
                        idf, self.join_func,
                        self.odf_confs, input_buf, join_buf, idx,
                        self.monitor_mode, self.monitor_topic))

        client_id = 'esm-{}'.format(self.graph_id)
        mqtt_conn = Client(client_id=client_id)
        mqtt_conn.on_connect = on_connect
        mqtt_conn.connect(config.mqtt_conf['host'],
                          port=config.mqtt_conf['port'])
        signal.signal(signal.SIGTERM, self._on_term(mqtt_conn))
        mqtt_conn.loop_forever()

    @staticmethod
    def _on_term(client):
        '''
        The signal handler for ``SIGTERM``

        :client: the ``paho.mqtt.Client`` instance

        Usage::

            signal.signal(signal.SIGTERM, self._on_term(client))

        '''
        def handler(signum, frame):
            log.info('terminating ESM process')
            handler.client.disconnect()

        handler.client = client
        return handler
