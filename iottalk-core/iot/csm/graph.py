import logging

from collections import deque
from functools import wraps
from itertools import starmap
from uuid import uuid4, UUID

from iot.conn import iot_conn_mgr
from iot.csm import ctrl
from iot.csm.base import BaseAPIHandler
from iot.csm.storage import Link, UserFunction
from iot.esm.worker import Worker

log = logging.getLogger('iottalk.graph')


class Graph(BaseAPIHandler):
    '''
    The graph api handler

    FIXME: the request-response model need timer for checking timeout.
    FIXME: stop the esm worker process if no link.
    '''

    def __init__(self, *args, **kwargs):
        self.funcs = []

        super(type(self), self).__init__(*args, **kwargs)

        self.esm_fixed_topic = self.esm_topic  # get a random generated topic
        self.esm_worker = Worker(graph_id=self.id)

    @property
    def esm_topic(self):
        return 'iottalk/esm/{}'.format(uuid4())

    def on_req(self, client, userdata, msg):
        payload = msg.payload

        log.debug('Graph request: %r', payload)

        # FIXME: check payload format
        opcode = payload['op']
        if opcode == 'attach':
            log.warning('client attach again, ignore.')
        elif opcode == 'detach':
            self.detach()
        else:
            op_func = getattr(self, 'op_{}'.format(opcode), None)

            # unknown op code
            if op_func is None:
                return self.unknown_op(payload, opcode)

            op_func(payload)

    def response_func(self, payload_tmpl, on_success=None, on_error=None):
        '''
        Wrap functions as partial functions that accept a payload parameter.

        Those functions are handlers of device response.
        A handler should accept the first argument as ``payload`` which
        is a dict make from ``payload_tmpl`` and the real response from device
        application, and return a payload which will be sent as the response of
        this api call.

        :param payload_tmpl: the payload template.
        :param on_success: the callback handler on success. if ``None``,
            use ``wrapper`` as default callback.
        :param on_error: the callback handler on error. if ``None``,
            use ``wrapper`` as default callback.
        :return: the ``(on_success, on_error)`` pair
        :rtype: tuple
        '''
        def factory(func):
            def wrapper(payload):
                msg_id = payload['msg_id']
                log.debug('The response msg_id: %r', msg_id)

                del payload['msg_id']
                wrapper.tmpl.update(payload)

                response = func(wrapper.tmpl.copy()) if func else wrapper.tmpl

                log.debug('The payload template for %r callback: %r',
                          msg_id, wrapper.tmpl)
                log.debug('The response of %r api call: %r', msg_id, response)

                return wrapper.res(response)

            wrapper.tmpl = payload_tmpl.copy()
            wrapper.res = self.res

            return wraps(func)(wrapper) if func else wrapper

        return factory(on_success), factory(on_error)

    def get_mode(self, keys):
        '''
        Determine *mode* (idf or odf) for the ``keys`` tuple

        :param keys: iterable
        :return: ``idf`` or ``odf``
        :raise: ``ValueError`` if non-deterministic
        '''
        modes = ('idf', 'odf')
        mode = None

        for k in keys:
            if k in modes and mode is None:
                mode = k
            elif k in modes and mode:
                raise ValueError('mode duplicated')

        if mode is None:
            raise ValueError('mode "idf" or "odf" not found')

        return mode

    def send_error(self, payload, reason):
        '''
        Send the error response
        '''
        payload['state'] = 'error'
        payload['reason'] = reason
        return self.res(payload)

    def op_add_link(self, payload):
        '''
        This add link command will send a ``CONNECT`` control message
        to device application.

        We will check the device feature lock as first.
        Then, record the link to ``Link`` for future lookup.
        '''
        da_id = UUID(payload['da_id'])
        mode = self.get_mode(payload.keys())
        feature = payload[mode]
        link_key = (payload['da_id'], feature, mode)

        try:
            ref, topic = Link.add(*link_key, self.id)
        except ValueError as e:
            return self.send_error(payload, reason=str(e))

        if payload.get('func') and not UserFunction.select(payload['func']):
            return self.send_error(
                payload, reason='Function unknown. Please add it first.')

        # when ref is 1, we need to send CONNECT signal at this timing.
        if ref == 1:
            topic = self.esm_topic
            Link.set(*link_key, topic)
            log.debug('ESM topic for %s: %s(%s) -> %s', mode, da_id, feature, topic)

            # like the idea of message passing, just copy the data
            conn = iot_conn_mgr.conns.getcopy(da_id)
            if conn:
                pub = conn.ctrl.pub
                msg_id = str(uuid4())  # random
                ctrl.connect(msg_id, mode, feature, topic, pub)
        payload['state'] = 'ok'
        return self.res(self._update_esm(payload, topic))

    def _update_esm(self, payload, topic):
        '''
        (re)configure and (re)start esm worker

        :return: ``payload``
        '''
        da_id = payload['da_id']
        mode = self.get_mode(payload)
        feature = payload[mode]
        input_type = payload.get('input_type')
        digest = payload.get('func')
        param_no = payload['param_no']
        tag_param_no = payload['tag_param_no']

        func = UserFunction.select(digest) if digest else None

        # dependency injection
        deps = tuple((UserFunction.select(sha), alias)
                     for alias, sha in payload.get('depends', {}).items())
        for src, alias in deps:
            if src:
                log.debug("_update_esm: get func alias %s ->\n %s", alias, src)
                continue
            payload['state'] = 'error'
            payload['reason'] = 'dependency {} not found'.format(alias)
            return payload

        conf = {
            'id': (da_id, feature),
            'input_type': input_type,
            'src': func,
            'topic': topic,
            'deps': deps,
            'param_no': param_no,
            'tag_param_no': tag_param_no,
        }
        if input_type is None:
            del conf['input_type']

        try:
            if mode == 'idf':
                self.esm_worker.add_idf_conf(conf)
            elif mode == 'odf':
                self.esm_worker.add_odf_conf(conf)
            self.esm_worker.start()
            log.debug('Graph._update_esm, topic %s', topic)
        except Exception as e:  # TODO: we need to remove this try-block someday
            payload['state'] = 'error'
            payload['reason'] = str(e)

        return payload

    def op_rm_link(self, payload):
        '''
        This ``rm_link`` command will send a ``DISCONNECT`` control message
        to device application.

        Different from ``add_link``, ``rm_link`` will remove config directly
        to avoid device ignoring ``DISCONNECT`` signal and sending data
        continuously.
        '''
        da_id = payload['da_id']
        mode = self.get_mode(payload)
        feature = payload[mode]
        link_key = (da_id, feature, mode)

        if Link.select(*link_key, self.id) is None:
            return self.send_error(payload, reason='link unknown')

        _, state = Link.select(*link_key)
        try:
            link_ref = Link.rm(*link_key, self.id)
        except ValueError as err:
            return self.send_error(payload, reason=str(err))

        if link_ref == 0:  # send DISCONNECT signal, reguardless the state
            self.esm_worker.rm_conf((da_id, feature), mode)
            self.esm_worker.start()
            conn = iot_conn_mgr.conns.getcopy(UUID(payload['da_id']))
            if conn:
                pub = conn.ctrl.pub
                msg_id = str(uuid4())  # random
                ctrl.disconnect(msg_id, mode, feature, 'unused', pub)
        elif isinstance(state, str):  # a real topic
            self.esm_worker.rm_conf((da_id, feature), mode)
            self.esm_worker.start()

        payload['state'] = 'ok'
        return self.res(payload)

    def op_add_funcs(self, payload):
        '''
        Add functions into in-memory storage.
        '''
        codes, digests = payload['codes'], payload['digests']
        if payload.get('aliases'):
            log.warning(
                'add_funcs got deprecated field `aliases` from payload %s',
                payload['aliases'])

        if len(codes) != len(digests):
            return self.send_error(
                payload, 'The numbers of codes and digests are not consistant')

        deque(starmap(UserFunction.add, zip(digests, codes)),
              maxlen=0)
        return self.res({
            'op': 'add_funcs',
            'state': 'ok',
            'digests': digests,
        })

    def op_rm_funcs(self, payload):
        '''
        Remove functions from in-memory storage.
        '''
        digests = payload['digests']

        deque(map(UserFunction.rm, digests), maxlen=0)
        return self.res({
            'op': 'rm_funcs',
            'state': 'ok',
            'digests': digests,
        })

    def ck_field_new(func):
        '''
        Decorator for checking field ``new`` function digest
        '''
        @wraps(func)
        def wrapper(self, payload, *args, **kwargs):
            if payload.get('new') is None:
                return func(self, payload, *args, **kwargs)

            _func = UserFunction.select(payload['new'])
            if not _func:
                return self.send_error(payload, reason='New function not found')

            return func(self, payload, *args, **kwargs)

        return wrapper

    def ck_field_deps(func):
        '''
        Decorator for checking field ``depends``.

        It will inject ``deps`` as keyword argument.
        ``deps`` is a tuple of pair ``(src, alias)``.

        Reject if any of function sha unknown.
        '''
        @wraps(func)
        def wrapper(self, payload, *args, **kwargs):
            deps = payload.get('depends', {})
            deps_sha = deps.values()

            if not deps_sha:
                kwargs['deps'] = ()
                return func(self, payload, *args, **kwargs)

            deps_pair = [(sha, UserFunction.select(sha), alias)
                         for alias, sha in deps.items()]

            # check function src existence
            # if a sha is unknown, UserFunction.select returns `None`
            for sha, src, alias in deps_pair:
                if src:
                    continue

                reason = ('dependency {}({}) unknown'
                          ', please add it first').format(alias, sha)
                return self.send_error(payload, reason=reason)

            # reshape ``deps_pair`` to ``(src, alias)``
            # it's ``(sha, src, alias)`` previous.
            kwargs['deps'] = tuple((d[1], d[2]) for d in deps_pair)
            return func(self, payload, *args, **kwargs)

        return wrapper

    @ck_field_new
    @ck_field_deps
    def op_set_join(self, payload, deps=None):
        '''
        Setup or change the join function.

        If ``payload['prev']`` is not the same as current running in ESM
        process, we will reject this request.
        '''
        if self.esm_worker.join_func.get('digest') != payload['prev']:
            return self.send_error(payload, reason='`prev` field mismatch')

        # `new <- None` is allow
        if payload.get('new'):
            func = UserFunction.select(payload['new'])
        else:
            func = None

        # get ``func`` and ``deps`` compiled
        self.esm_worker.join_func = (func, deps)
        self.esm_worker.start()

        return self.res({
            'op': 'set_join',
            'prev': payload['prev'],
            'new': payload['new'],
            'depends': payload.get('depends', None),
            'state': 'ok',
        })

    @ck_field_new
    @ck_field_deps
    def op_set_df_func(self, payload, deps=None):
        '''
        Change the idf/odf function
        '''
        da_id = payload['da_id']
        mode = self.get_mode(payload.keys())
        feature = payload[mode]
        link_state = Link.select(da_id, feature, mode, self.id)

        if link_state is None:
            return self.send_error(
                payload,
                reason='Unknown link, please add_link first')

        conf_getter = getattr(self.esm_worker, 'get_{}_conf'.format(mode))
        df_conf = conf_getter(da_id, feature)
        if df_conf is None:  # FIXME
            return self.send_error(
                payload,
                reason='Maybe some race condition happend on df_conf')

        if df_conf.get('digest') != payload['prev']:
            return self.send_error(payload, reason='`prev` field mismatch')

        new_func = UserFunction.select(payload['new'])
        try:
            df_conf['src'] = new_func  # compile ``new_func``
            df_conf['deps'] = deps  # compile and inject dependencies
            df_conf['input_type'] = payload.get('input_type')
        except Exception:
            return self.send_error(
                payload,
                reason='Maybe some error in the functions.')

        if isinstance(link_state, str):  # not status code
            self.esm_worker.start()

        return self.res({
            'op': 'set_df_func',
            'da_id': payload['da_id'],
            mode: payload[mode],
            'new': payload['new'],
            'depends': payload.get('depends', None),
            'state': 'ok',
        })

    def op_start_monitor(self, payload):
        '''
        Turn the monitor mode on.
        '''
        if not self.esm_worker.monitor_mode:
            self.esm_worker.monitor_mode = True
            self.esm_worker.start()

        payload['monitor_topics'] = self.esm_worker.monitor_topic
        payload['state'] = 'ok'
        return self.res(payload)

    def op_stop_monitor(self, payload):
        '''
        Turn the monitor mode off.
        '''
        if self.esm_worker.monitor_mode:
            self.esm_worker.monitor_mode = False
            self.esm_worker.start()

        payload['state'] = 'ok'
        return self.res(payload)
