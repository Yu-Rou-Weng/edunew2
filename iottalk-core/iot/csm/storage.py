'''
This modules provide a thread dedicated to handling all i/o manipulation.

We consider this thread as a in-memory storage and use single thread
on i/o to keep away from using *lock* and race condition.
'''
import logging

from functools import wraps
from hashlib import sha256
from threading import Thread

import zmq

__all__ = ('Link', 'UserFunction')
log = logging.getLogger('iottalk.csm.storage')


class _IOThread(Thread):
    daemon = True

    def run(self):
        while True:
            try:
                self.dispatch()
            except Exception as err:
                log.exception('Unhandled exception in io thread: %r', err)
                self.dispatch_cleanup()

    def dispatch(self):
        '''
        Consuming the request from queue and

        A subclass should override this method.
        '''
        raise NotImplementedError()

    def dispatch_cleanup(self):
        '''
        Cleanup handler for ``dispatch`` got exception.

        A subclass should override this method
        '''
        pass


class _ReplyMixin(object):
    '''
    Reply Mixin

    create a ``self.rep`` zmq socket for request-reply model
    '''

    def __init__(self, *args, **kwargs):
        super(_ReplyMixin, self).__init__(*args, **kwargs)
        self.rep = zmq.Context.instance().socket(zmq.REP)

    def __del__(self):
        self.rep.close()

    def dispatch_cleanup(self):
        self.rep.send_pyobj(False)


class LinkCodeMixin(object):
    '''
    Link status code
    '''
    UNKNOWN = -1
    PENDING = 2


class _LinkThread(_ReplyMixin, _IOThread, LinkCodeMixin):

    def __init__(self):
        super(type(self), self).__init__()

        # 3-tuple and ``topic`` pair
        self.links = {}
        # 3-tuple and `set of graph_ids` pair
        self.refs = {}

        self.rep.bind('inproc://link')

    def dispatch(self):
        cmd, args = self.rep.recv_pyobj()

        if cmd == 'add':
            self.add(args)
        elif cmd == 'set':
            self.set(args)
        elif cmd == 'rm':
            self.rm(args)
        elif cmd == 'clear':
            self.clear()
        elif cmd == 'select':
            self.select(args)
        elif cmd == 'pop':
            self.pop(args)
        else:
            raise NotImplementedError()

    def add(self, link):
        '''
        :param link: ``tuple`` of
            ``(da_id, feature_name, feature_mode, graph_id)``.

        :return:
            ``(reference count, topic or status code)`` pair if success.
            ``False`` if conflict.
        '''
        key = link[0:3]
        gid = link[-1]

        state = self.links.get(key, None)  # current state
        if state is not None and gid in self.refs[key]:
            # check conflict
            return self.rep.send_pyobj(False)
        elif isinstance(state, str):
            # topic exists, but different graph_id
            ret = self.links[key]
        elif state is None:  # set to PENDING
            ret = self.links[key] = self.PENDING
        elif isinstance(state, int):  # already have status code
            ret = self.links[key]

        if key not in self.refs:  # init graph_ids set
            self.refs[key] = set()
        self.refs[key].add(gid)

        self.rep.send_pyobj((len(self.refs[key]), ret))

        log.debug('Links: %r', self.links)
        log.debug('Links count become: %s', len(self.refs[key]))

    def set(self, link):
        '''
        :param link: ``tuple`` of
            ``(da_id, feature_name, feature_mode, topic)``.

        If current ``topic`` is ``Link.PENDING``, set the confirmed topic,
        then return ``True``.

        If current ``topic`` is a ``str``, imply that the confirmed topic
        has been set already, return ``False`` as rejection.

        If current ``topic`` is ``None``, return ``None`` as rejection.
        '''
        key = link[0:3]
        topic = link[-1]

        state = self.links.get(key, None)  # current state
        if state is None:
            return self.rep.send_pyobj(None)
        elif isinstance(state, str):
            return self.rep.send_pyobj(False)
        elif state == self.PENDING:
            self.links[key] = topic
            return self.rep.send_pyobj(True)
        else:
            return self.rep.send_pyobj(self.UNKNOWN)

    def rm(self, link):
        '''
        :param link: ``(da_id, feature_name, feature_mode, graph_id)``

        :return:
            the reference count if success.
            ``False`` if conflict.
        '''
        key = link[0:3]
        gid = link[-1]

        if key not in self.links:
            self.rep.send_pyobj(False)
            return

        self.refs[key].remove(gid)

        count = len(self.refs[key])
        if count == 0:
            del self.links[key]
            del self.refs[key]

        self.rep.send_pyobj(count)
        return

    def clear(self):
        '''
        :return: True.
        '''
        self.links.clear()
        self.refs.clear()
        self.rep.send_pyobj(True)

    def select(self, link=None):
        if not link:
            self.rep.send_pyobj(self.links.copy())
            return

        if len(link) == 4:  # return ``topic`` only
            key = link[0:3]
            gid = link[-1]
            if key not in self.links or gid not in self.refs[key]:
                self.rep.send_pyobj(None)
            else:
                self.rep.send_pyobj(self.links[key])

        else:  # return ``(count, topic)`` pair
            if link not in self.links:
                self.rep.send_pyobj(None)
            else:
                self.rep.send_pyobj((len(self.refs[link]), self.links[link]))


class _FunctionThread(_ReplyMixin, _IOThread):
    '''
    The table of user defined functions

    :key: the sha256 hash of the function string
    :src: function source
    '''

    def __init__(self):
        super(type(self), self).__init__()

        self.funcs = {}
        self.rep.bind('inproc://function')

    def __del__(self):
        self.rep.close()

    def dispatch(self):
        cmd, args = self.rep.recv_pyobj()

        if cmd == 'add':
            self.add(*args)
        elif cmd == 'rm':
            self.rm(args)
        elif cmd == 'clear':
            self.clear()
        elif cmd == 'select':
            self.select(args)
        else:
            raise NotImplementedError()

    def add(self, key, src):
        '''
        :param key: the sha256 of function source.
        :param src: function source

        :return: False if the key exists.
            True if adding successfully.
        '''
        if key in self.funcs:
            self.rep.send_pyobj(False)
            return

        self.funcs[key] = src
        self.rep.send_pyobj(True)

    def rm(self, key):
        if key not in self.funcs:
            self.rep.send_pyobj(False)
            return

        del self.funcs[key]
        self.rep.send_pyobj(True)

    def clear(self):
        self.funcs.clear()
        self.rep.send_pyobj(True)

    def select(self, key=None):
        '''
        :param key: sha256 of function or ``None`` for selecting all functions.
        :return: ``source`` as a str.
        '''
        # select all
        if key is None:
            return self.rep.send_pyobj(self.funcs.copy())
        else:
            src = self.funcs.get(key, None)
            return self.rep.send_pyobj(src)


def _init_threads():
    link_thread = _LinkThread()
    link_thread.start()

    func_thread = _FunctionThread()
    func_thread.start()


def _req(url):
    '''
    Decorator factory for connect REQ zmq socket to ``url``
    '''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with zmq.Context.instance().socket(zmq.REQ) as req:
                req.connect(url)
                return func(*args, req=req, **kwargs)

        return wrapper

    return decorator


class Link(LinkCodeMixin):
    '''
    A link denote a connection from device feature to a MQTT topic.

    :key: (da_id, feature_name, feature_mode, graph_id)
    :value: topic

    The tuple of ``(da_id, feature_name, feature_mode)`` can consider as
    a one to one mapping to a ``topic``.
    The ``graph_id`` is for reference counting.
    Caller can keep ``add`` with same ``(da_id, feature_name, feature_mode)``
    tupple but with different ``graph_id``. This operation is legit.
    And it denote that plus one to the reference counter of the ``topic``.

    The return of ``add`` operator may be a string or a int of status
    code.
    - sting is for a DA confirmed topic.
    - status code represents a unconfirm status.
    '''

    @staticmethod
    @_req('inproc://link')
    def add(da_id, feature_name, feature_mode, graph_id, req=None):
        '''
        Add link

        If the current state of link is ``Link.PENDING``, which means we still
        waiting for CONNECT signal of Device Application finished,

        If add with a new 3-tuple key, this function always return
        ``Link.PENDING``. Caller need to use ``set`` to set the
        final correct ``topic``.

        :return: ``(reference count, value)``, where value could be:
            * ``topic`` (str) if add link successfully

            * ``Link.PENDING`` (int) if waiting for DA CONNECT.

        :raise ValueError: if the link conflicts
        '''
        args = (da_id, feature_name, feature_mode, graph_id)
        req.send_pyobj(('add', args))
        res = req.recv_pyobj()

        if res is False:
            raise ValueError('link already exists')
        return res

    @staticmethod
    @_req('inproc://link')
    def set(da_id, feature_name, feature_mode, topic, req=None):
        '''
        Set topic to link

        :raise ValueError:
            * If the link do not exist

            * If the topic is set to string already (not status code)

        :return: ``True``
        '''
        args = (da_id, feature_name, feature_mode, topic)
        req.send_pyobj(('set', args))
        res = req.recv_pyobj()

        if res is None:
            raise ValueError('link do not exist')
        elif res is False:
            raise ValueError('topic already sets')
        return res

    @staticmethod
    @_req('inproc://link')
    def rm(da_id, feature_name, feature_mode, graph_id, req=None):
        '''
        :raise ValueError: if the link is unknown

        :return: the reference count after removing
        '''
        args = (da_id, feature_name, feature_mode, graph_id)
        req.send_pyobj(('rm', args))
        res = req.recv_pyobj()

        if res is False:
            raise ValueError('link unknown')
        return res

    @staticmethod
    @_req('inproc://link')
    def clear(req):
        req.send_pyobj(('clear', None))
        return req.recv_pyobj()

    @staticmethod
    @_req('inproc://link')
    def select(da_id=None, feature_name=None, feature_mode=None, graph_id=None,
               req=None):
        '''
        Get a snapshot of ``self.links`` or query a topic with specific key

        :param args:
            * 3-tuple ``(da_id, feature_name, feature_mode)``
            * 4-tuple with ``graph_id``

        :return:
            * 3-tuple: ``(reference count, topic)`` pair
            * 4-tuple: ``topic``
            * ``None`` as default fallback
        '''
        if da_id and feature_name and feature_mode:
            if graph_id:
                args = (da_id, feature_name, feature_mode, graph_id)
            else:
                args = (da_id, feature_name, feature_mode)
        else:
            args = None
        req.send_pyobj(('select', args))
        return req.recv_pyobj()


class UserFunction(object):
    '''
    The user defined functions.

    :key: sha256 hash of the function string
    :src: function source
    :alias: function name for ESM context interpolation.
    '''

    @classmethod
    @_req('inproc://function')
    def add(cls, key, src, req=None):
        '''
        :return: False if function already exists.  True if successful.
        :raise ValueError: if function hash mismatched or key duplicated.
        '''
        if key != cls._func_key(src):
            raise ValueError('function hash mismatched')

        req.send_pyobj(('add', (key, src)))
        res = req.recv_pyobj()
        return res

    @staticmethod
    @_req('inproc://function')
    def rm(key, req):
        '''
        :return: False if ``key`` is unknown.
        '''
        req.send_pyobj(('rm', key))
        res = req.recv_pyobj()

        return res

    @staticmethod
    @_req('inproc://function')
    def clear(req):
        req.send_pyobj(('clear', None))
        return req.recv_pyobj()

    @staticmethod
    @_req('inproc://function')
    def select(key=None, req=None):
        req.send_pyobj(('select', key))
        return req.recv_pyobj()

    @staticmethod
    def _func_key(src):
        '''
        The the sha256 hash value from a function string
        '''
        return sha256(src.encode('utf-8')).hexdigest()


# a global queue for storing ``add_link``/``rm_link`` callback
# It should be *only* used in single thread, currently csm thread.
# structure:
# {
#    (3-tuple key): {'graph_id': function}
# }
add_link_cb = {}


_init_threads()
