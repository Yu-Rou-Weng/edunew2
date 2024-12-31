'''
This module implements a set of Connection Managers.

Connection manager provides a in-memery loopup table for connections.

FIXME: There are lots of thread-safety issues on operating the
       singleton ``iot_conn_mgr``.
       A better solution to the need of "getting value for update" is
       re-write the whole model with an request queue.
       See https://gitlab.com/IoTtalk/iottalk-core/merge_requests/98#note_209041690
'''
import json
import logging

from abc import ABCMeta, abstractmethod
from copy import copy
from functools import partial, wraps
from six import string_types
from six.moves import UserDict
from threading import Lock, Timer
from uuid import UUID, uuid4

from iotutils.mqtt import JsonClient, mqtt_json_payload
from tornado.httpclient import HTTPClient, HTTPError
from zope import event as zevent

from iot import events
from iot.config import config
from iot.csm import ctrl
from iot.csm.storage import Link
from iot.utils import suppress

log = logging.getLogger('iottalk.conn')


class DevAppState:
    NOTHING = 0
    ONLINE = 1
    OFFLINE = 2

    @classmethod
    def to_str(cls, x):
        if x == cls.NOTHING:
            return 'nothing'
        elif x == cls.ONLINE:
            return 'online'
        elif x == cls.OFFLINE:
            return 'offline'

        raise ValueError('Unknown DevAppState code: {}'.format(x))


class DataConnMap(UserDict):
    '''
    The dictionary store all data connections

    If we request a non-exist key,
    the connection container will be auto-created.

    >>> data_conn = DataConnMap()
    >>> data_conn['meow']
    <Feature Conn Container: meow>
    >>> data_conn['meow'].i
    >>> data_conn['meow'].o

    >>> data_conn.get('meow')
    <Feature Conn Container: meow>

    >>> data_conn.get('acce', None) is None
    True

    >>> 'meow' in data_conn
    True
    >>> 'acce' in data_conn
    False
    '''

    class Feature(object):
        i = None  # input
        o = None  # output

        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return '<Feature Conn Container: {}>'.format(self.name)

    def get(self, key, default=None):
        '''
        :type key: str
        '''
        if not isinstance(key, string_types):
            return default
        elif key not in self:
            return default
        return self[key]

    def __missing__(self, key):
        ret = self.Feature(key)
        self.data[key] = ret
        return ret


class Conn(object):
    '''
    The connection class used in ``ConnMap``

    :param id_: the ``UUID`` object

    >>> id_ = UUID('a54b5bf9-c39b-4248-b611-80d1ed4a36df')
    >>> c = Conn(id_)
    >>> c.id
    UUID('a54b5bf9-c39b-4248-b611-80d1ed4a36df')

    >>> # data channel is here
    >>> c.data
    {}
    >>> c.data['meow']  # feature auto-created
    <Feature Conn Container: meow>

    >>> # control channel is here
    >>> isinstance(c.ctrl, CtrlConn)
    True

    >>> c.conf
    {}
    '''

    def __init__(self, id_):
        self.id = id_
        self.ctrl = CtrlConn(id_=id_)
        self.data = DataConnMap()
        self.conf = {}


class DevAppTimer(Timer):
    daemon = True

    def clone(self):
        '''
        Clone a new Timer
        '''
        return DevAppTimer(self.interval, self.function)


class CtrlConn(object):
    '''
    The control channel connection object.

    :param id_: the ``UUID`` object
    :param pub: the publish function with the spec same as
                ``paho.mqtt.client.Client.publish``.
    :param sub: the subscribe helper function. It must have a function
                attribute ``remove_callback`` in order to reset callback.
    :param rev: the ``revision`` token for checking race condition.

    >>> def pub(*args):
    ...     pass

    >>> def sub(*args):
    ...     pass

    >>> # sub function must have ``remove_callbacks``
    >>> sub.remove_callback = (lambda : 42)

    >>> id_ = UUID('a54b5bf9-c39b-4248-b611-80d1ed4a36df')

    >>> cc = CtrlConn(id_, pub, sub, rev=42)
    >>> cc.pub is pub
    True
    >>> cc.sub is sub
    True
    >>> assert cc.rev == 42
    '''

    def __init__(self, id_, pub=None, sub=None, rev=None):
        self.id = id_
        self.pub = pub
        self.sub = sub
        self.da_state = DevAppState.OFFLINE
        self.da_state_lock = Lock()
        self.rev = rev
        self.exp_timer = DevAppTimer(  # the expiration timer
            config.da_expiration, self._handle_da_expr)

    @property
    def sub(self):
        return getattr(self, '_sub', None)

    @sub.setter
    def sub(self, val):
        if val is None:
            return
        if getattr(self, '_sub', None):
            self._sub.remove_callback()

        self._sub = val
        self._sub(self._on_message)

    @mqtt_json_payload(raise_error=False)
    def _on_message(self, client, userdata, msg):
        '''
        The subscribe message callback

        We accept json format.

        The device application should send MQTT retained messages when the
        connection state changed::

            {
                'state': 'online|offline',
                'rev': 'the rev field from registration',
            }

        * ``online``: should be sent right after the device application
          connects to the MQTT server

        * ``offline``: should be sent as the "Last Will Message" right after the
          device application connects to the MQTT server

        * ``rev``: this field is used for stripping out out-of-date message.

        For the response of other command messages, please checkout
        ``iot.csm.ctrl``
        '''
        id_ = msg.topic.split('/')[0]
        data = msg.payload

        log.debug('connmgr on_mesaage %s: %s', id_, data)

        # check revision
        if data['state'] in ('online', 'offline'):
            rev = data.get('rev')
            if self.rev != rev:
                log.warning(
                    'Device application %s '
                    'state msg revision unknown or out-of-date, dropping',
                    id_)
                return

        new_state = data['state']

        if new_state == 'online':
            self.transit_online()
        elif new_state == 'offline':
            self.transit_offline()
        else:
            if config.debug:
                log.debug('got malformated message %s', data)
            else:
                log.info('got malformated message')

        log.info('Device application %s state: %s', id_, data['state'])

    def reset_exp_timer(self):
        self.exp_timer.cancel()
        self.exp_timer = self.exp_timer.clone()
        return self.exp_timer

    def _handle_da_expr(self):
        '''
        In the case that device application cannot send DELETE deregister
        request and got timeout. We will execute the deregister process in
        server side.

        FIXME: the timer still runing event HTTP server got DELETE request from
               device application.
               In the log, there was some warning generated by
               this DELETE attempts.
               Maybe this issue can be solved by switching to GC policy,
               not a plain timer.
        '''
        log.info('DA %s got offline timeout, execute the deregister process',
                 self.id)

        self.transit_deregister()

        try:
            http_client = HTTPClient()
            host = 'localhost' if config.bind == '0.0.0.0' else config.bind
            http_client.fetch(
                'http://{}:{}/{}'.format(host, config.http_port, self.id),
                method='DELETE',
                headers={'Content-Type': 'application/json'},
                body=json.dumps({'rev': self.rev}),
                allow_nonstandard_methods=True
            )
        except HTTPError as e:
            log.warning('Device application %s DELETE request failure: %s',
                        self.id, e)
        finally:
            http_client.close()

    def _state_transition(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cur_state = DevAppState.to_str(self.da_state)
            with self.da_state_lock:
                ret = func(self, *args, **kwargs)
            new_state = DevAppState.to_str(self.da_state)

            if cur_state != new_state:
                log.debug('DA %s state changed: %s -> %s',
                          self.id, cur_state, new_state)
            return ret

        return wrapper

    @_state_transition
    def transit_register(self):
        zevent.notify(events.DevAppRegister(self.id))
        self.reset_exp_timer()
        self.exp_timer.start()
        self.da_state = DevAppState.OFFLINE

    @_state_transition
    def transit_online(self):
        if self.da_state != DevAppState.ONLINE:
            zevent.notify(events.DevAppOnline(self.id))
            self.reset_exp_timer()
            self.da_state = DevAppState.ONLINE

        # connect/reconnect, send link connect signal
        links = Link.select()
        for link in links:
            id_, feature, mode = link
            topic = links.get(link)
            if id_ == str(self.id):
                ctrl.connect(str(uuid4()), mode, feature, topic, self.pub)

    @_state_transition
    def transit_offline(self):
        if self.da_state == DevAppState.OFFLINE:
            return

        zevent.notify(events.DevAppOffline(self.id))
        self.exp_timer.start()
        self.da_state = DevAppState.OFFLINE

    @_state_transition
    def transit_deregister(self):
        if self.da_state != DevAppState.NOTHING:
            self.reset_exp_timer()

        self.da_state = DevAppState.NOTHING
        # clean up
        self.sub.finalize()


class ConnMap(UserDict):
    '''
    The mapping uses ``uuid.UUID`` as key.

    Structure::

        {
            UUID('...'): {
                'ctrl': (<publish function>, <subscribe function>),
                'data': {
                    'feature': {
                        'i': <connection object>,
                        'o': <connection object>,
                    }.
                },
                'conf': {
                    'ctrl': {
                        'scheme': 'mqtt',
                        'host': 'localhost',
                        ...
                    },
                    'feature': {
                        ...
                    },
                },
            },
            ...
        }
    '''

    def confs(self):
        '''
        :return: a ``ItemsView`` for ``(uuid, conf)`` pairs.
        '''
        raise NotImplementedError

    def data_channs(self):
        '''
        :return: a ``ItemsView`` for ``(uuid, data_channs)`` pairs.
        '''

    def ctrl_channs(self):
        '''
        :return: a ``ItemsView`` for ``(uuid, ctrl_channs)`` pairs.
        '''

    def get(self, key, default=None):
        '''
        :type key: ``UUID``
        '''
        if not isinstance(key, UUID):
            return default
        return self[key]

    def getcopy(self, *args, **kwargs):
        val = self.get(*args, **kwargs)
        return copy(val)

    def __getitem__(self, key):
        '''
        :param key: we accept key as an ``UUID``.
        :raise TypeError: if key is not an ``UUID`` object.
        '''
        if not isinstance(key, UUID):
            raise TypeError(
                'key should be an UUID object, not {!r}'.format(type(key)))

        if key not in self.data:
            return self.__missing__(key)
        return self.data[key]

    def __missing__(self, key):
        '''
        Auto create the ``Conn`` object
        '''
        ret = Conn(key)
        self.data[key] = ret
        return ret


class ConnMgrBase(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.__conns = ConnMap()
        super(ConnMgrBase, self).__init__()

    def __del__(self):
        with suppress(AttributeError):
            super(ConnMgrBase, self).__del__()

    @property
    def conns(self):
        '''
        Get all managed connections
        '''
        return self.__conns

    @abstractmethod
    def setup_conn(self, proto, conn_conf):
        '''
        Create a connect which will be managed by connection manager
        '''


class MQTTConnMgrMixin(object):
    '''
    Connection Manager MQTT Mixin

    .. todo::
        - reconnect
    '''

    _mqtt_c = None

    def __init__(self):
        super(MQTTConnMgrMixin, self).__init__()
        self.mqtt_connected = False
        self.mqtt_conn_prev = False  # connection prev state
        self.subscribed_topic = set()  # {(topic, qos), ...}

    def __del__(self):
        with suppress(AttributeError):
            super(MQTTConnMgrMixin, self).__del__()

        if self.mqtt_c is not None:
            self.mqtt_c.disconnect()
            self.mqtt_c.loop_stop()

    @property
    def mqtt_c(self):
        '''
        The ``paho.mqtt.client.Client`` instance
        '''
        if self._mqtt_c is None:
            raise AttributeError(
                'Please create client via ``setup_mqtt_conn`` first.')
        return self._mqtt_c

    def setup_mqtt_conn(self, *args, client_id=config.session_id, **kwargs):
        '''
        Setup a mqtt connection and manage it.

        For the available parameters, please check out
        :py:class:`paho.mqtt.client.Client`

        A var ``self._mqtt_c`` will be setup.

        This call will block until the mqtt server connected.
        '''
        self._mqtt_c_lock = Lock()
        self._mqtt_c_lock.acquire()

        client = JsonClient(client_id='connmgr-{}'.format(client_id))
        # Set reconnect interval
        client.reconnect_delay_set(min_delay=5, max_delay=30)
        if config.enable_mqtt_auth:
            client.username_pw_set('ec', config.aaa_token)

        client.on_connect = self.mqtt_on_connect
        client.on_disconnect = self.mqtt_on_disconnect
        client.on_subscribe = self.mqtt_on_subscribe

        client.connect(*args, **kwargs)
        client.loop_start()

        self._mqtt_c = client
        if not self._mqtt_c_lock.acquire(timeout=10):
            raise RuntimeError('Connect to mqtt server timeout')
        del self._mqtt_c_lock

    def mqtt_on_connect(self, client, userdata, flags, rc):
        '''
        The MQTT client connect callback
        '''
        if rc != 0:
            if hasattr(self, '_mqtt_c_lock'):
                # we do not have _mqtt_c_lock if reconnecting
                self._mqtt_c_lock.release()
            msg = 'MQTT server connection refused, code {}'.format(rc)
            log.error(msg)
            raise IOError(msg)

        log.info('Connect to mqtt server successfully')

        if self.mqtt_conn_prev:  # in case of reconnection
            for topic, qos in self.subscribed_topic:
                log.info('Renew subscriptions %s', topic)
                self.mqtt_c.subscribe(topic, qos=qos)

        self.mqtt_connected = True

        if hasattr(self, '_mqtt_c_lock'):
            # we do not have _mqtt_c_lock if reconnecting
            self._mqtt_c_lock.release()

    def mqtt_on_disconnect(self, client, userdata, rc):
        '''
        The MQTT client disconnect callback
        '''
        if rc != 0:
            log.warning('Disconnected from the MQTT broker unexpectedly')
        log.info('MQTT server disconnected')
        self.mqtt_conn_prev = self.mqtt_connected
        self.mqtt_connected = False

    def mqtt_on_subscribe(self, client, userdata, mid, granted_qos):
        '''
        :param mid: the message id returned by ``Client.subscribe``
        '''
        for qos in granted_qos:
            if qos not in (0, 1, 2):
                log.warning('Subscribe failed')

    def mqtt_sub(self, id_, feature, topic, qos=2):
        '''
        Subscribe to a mqtt topic.

        :param id_: the ``UUID`` object
        :param feature: the feature name, if feature name is ``_ctrl``, we will
                        setup the control channel.
        :param topic: the mqtt topic, e.g: ``uuid/feature/i``.
        :param qos: the mqtt qos level, should be 0, 1, 2
        :param ctrl: control channel or not
        :return: a function accept a *on message* callback.
                 This returned function also has following
                 function attributes:

                 :func.cb: the using callback will be stored here.
                 :func.client: the ``paho.mqtt.client.Client`` instance
                 :func.feature: the feature name related to the subscription
                 :func.id: the ``UUID`` object
                 :func.remove_callback: the function for unsubscribing topic
                 :func.topic: the mqtt topic
                 :func.qos: qos level
                 :func.finalize: the function for finalize mqtt connection resource
        '''
        def f(callback):
            if f.cb is not None:
                f.client.message_callback_remove(f.topic)
            f.client.message_callback_add(f.topic, callback)
            f.cb = callback
            log.info('connmgr msg callback setup %s', f.id)
            return callback

        def remove_callback():
            f.client.message_callback_remove(f.topic)
            # we still cannot unsubscribe the ``f.topic`` here,
            # since the ``f`` might be reused.

            # TODO: write a test case that adding callback, remove callback
            #       then add a callback again.

        def finalize():
            remove_callback()
            self.subscribed_topic.remove((f.topic, f.qos))
            f.client.unsubscribe(f.topic)

        f.cb = None
        f.client = self.mqtt_c
        f.feature = feature
        f.id = id_
        f.topic = topic
        f.qos = qos
        f.remove_callback = remove_callback
        f.finalize = finalize

        if topic not in self.subscribed_topic:
            self.mqtt_c.subscribe(topic, qos=qos)
            self.subscribed_topic.add((topic, qos))

        if feature != '_ctrl':
            self.conns[id_].data[feature].i = f
        else:
            self.conns[id_].ctrl.sub = f

        return f

    def mqtt_pub(self, id_, feature, topic, qos=2):
        '''
        Add a publish function to ``self.conns``.

        :param id_: the ``UUID`` object
        :param feature: the feature name, if feature name is ``_ctrl``, we will
                        setup the control channel
        :param ctrl: control channel or not
        :type topic: str

        :return: the ``publish`` function
        '''
        if feature != '_ctrl':
            pub = partial(self.mqtt_c.publish, topic, qos=qos)
            self.conns[id_].data[feature].o = pub
        else:
            pub = partial(self.mqtt_c.publish_json, topic, qos=qos)
            self.conns[id_].ctrl.pub = pub

        return pub

    def mqtt_ctrl(self, id_, pub_topic, sub_topic, rev):
        '''
        :param id_: the ``UUID`` object
        :param pub_topic:
        :param sub_topic:
        :param rev:
        '''
        pub = self.mqtt_pub(id_, '_ctrl', pub_topic)
        sub = self.mqtt_sub(id_, '_ctrl', sub_topic)
        self.conns[id_].ctrl.rev = rev
        self.conns[id_].ctrl.transit_register()
        return pub, sub


class WSConnMgrMixin(object):
    '''
    Connection Manager WebSocket Mixin
    '''

    def __init__(self):
        super(WSConnMgrMixin, self).__init__()

    def __del__(self):
        with suppress(AttributeError):
            super(WSConnMgrMixin, self).__del__()

    def setup_ws_conn(self, conf):
        '''
        Setup a websocket connection and manage it.

        :param conf: TBD
        '''
        raise NotImplementedError()


class IoTConnMgr(ConnMgrBase, MQTTConnMgrMixin, WSConnMgrMixin):
    '''
    IoTtalk Connection Manager
    '''

    def __init__(self, auto_connect=True):
        '''
        .. todo::
            - make ``keepalive`` configurable

        :param auto_connect: initialize with MQTT borker connection.
            The case of disabled is for testing.
        '''
        super(IoTConnMgr, self).__init__()

        if auto_connect:
            self.setup_conn(
                'mqtt', config.mqtt_conf['host'],
                port=config.mqtt_conf['port'], keepalive=60)

    def __del__(self):
        with suppress(AttributeError):
            super(IoTConnMgr, self).__del__()

    def setup_conn(self, proto, *args, **kwargs):
        '''
        Create a connect which will be managed by connection manager

        :param proto: ``mqtt`` or ``websocket``
        :param conn_conf: a dict represent the config of connection
        '''
        proto = proto.lower()

        if proto == 'mqtt':
            self.setup_mqtt_conn(*args, **kwargs)
        elif proto == 'websocket':
            self.setup_ws_conn(*args, **kwargs)
        else:
            raise NotImplementedError(
                'Protocol {!r} not supported'.format(proto))


# make a singleton
iot_conn_mgr = IoTConnMgr()
