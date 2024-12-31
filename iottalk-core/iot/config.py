'''
The configuration system.

If we have any setting that require affect whole IoTtalk system or the config
require IoTtalk to restart, those configs should place here.

This module will export a singleton of ``Config`` -- ``config``.
'''
import logging
import os

from configparser import ConfigParser, ExtendedInterpolation
from contextlib import suppress
from uuid import uuid4

from pony.orm import Database
from six import string_types

from iot import utils

__all__ = ('config',)

log = logging.getLogger('iottalk.config')


class Config(object):
    '''
    Main configuration here.

    If a property consider as *readonly*, we will use ``property`` decorator
    for it.

    This class is responsible to setup user config dir.
    On Unix, we will have ``$HOME/.iottalk``;
    on windows, it is ``$USERPROFILE/_iottalk``.
    '''

    __aaa_token = ''
    __enable_mqtt_auth = False
    __gateway_port = 17000
    __beacon_port = 1900
    __http_port = 9992
    __bind = '0.0.0.0'
    __uuid = ''
    debug = False
    __db_conf = {
        'type': 'sqlite',  # or `mysql`
        'url': 'iottalk.db',
        'host': 'localhost',
        'port': -1,
        'user': '',
        'passwd': '',
    }
    __db = None
    __userdir = ''
    __mqtt = {
        'scheme': 'mqtt',
        'host': 'localhost',
        'port': 1883,
    }
    __ws = {
        'scheme': 'ws',
        'host': __mqtt['host'],
        'port': 1884,
    }
    __session_id = uuid4()  # read-only
    __da_expiration = 86400 * 3  # 3 days

    def __init__(self):
        ...

    @property
    def userdir(self):
        if self.__userdir:
            return self.__userdir

        if utils.is_posix():
            self.__userdir = os.path.join(os.environ['HOME'],
                                          '.iottalk')
        elif utils.is_win():
            self.__userdir = os.path.join(os.environ['USERPROFILE'],
                                          '_iottalk')
        else:
            raise OSError('Unsupport os type "{}"'.format(os.name))
        self.setup_userdir()

        return self.__userdir

    @userdir.setter
    def userdir(self, val):
        self.__userdir = val
        self.setup_userdir()

    def setup_userdir(self):
        path = self.userdir

        if os.path.exists(path) and not os.path.isdir(path):
            raise OSError('Path "{}" is not a dir'.format(path))
        elif os.path.exists(path) and os.path.isdir(path):
            return

        os.mkdir(path)

    @property
    def aaa_token(self):
        return self.__aaa_token

    @aaa_token.setter
    def aaa_token(self, aaa_token):
        self.__aaa_token = aaa_token

    @property
    def enable_mqtt_auth(self):
        return self.__enable_mqtt_auth

    @enable_mqtt_auth.setter
    def enable_mqtt_auth(self, enable_mqtt_auth):
        """
        :param enable_mqtt_auth: Whether the mqtt auth is enabled or not
        :type enable_mqtt_auth: ``bool``
        """
        self.__enable_mqtt_auth = enable_mqtt_auth

    @property
    def gateway_port(self):
        return self.__gateway_port

    @property
    def beacon_port(self):
        return self.__beacon_port

    @property
    def beacon_url(self):
        return 'udp://{}:{}'.format(self.ip, self.beacon_port)

    @property
    def bind(self):
        return self.__bind

    @bind.setter
    def bind(self, val):
        self.__bind = val

    @property
    def uuid(self):
        '''
        :TODO: load the uuid from config file.
        '''
        if not self.__uuid:
            self.__uuid = uuid4()
        return self.__uuid

    @property
    def http_port(self):
        return self.__http_port

    @http_port.setter
    def http_port(self, val):
        self.__http_port = val

    @property
    def db(self):
        '''
        :return: The pony orm db instance without db provider binding
        '''
        if not self.__db:
            self.__db = Database()

        return self.__db

    @property
    def db_conf(self):
        '''
        The db cononection configuration.
        Here is the schema::

            {
                'type': str,
                'url': str,
                'host': str,
                'port': int,
                'user': str,
                'passwd': str,
            }

        >>> config.db_conf = {'type': 'answer', 'port': 42}
        >>> assert config.db_conf['type'] == 'answer'
        >>> config.db_conf['port']
        42
        '''
        return self.__db_conf.copy()

    @db_conf.setter
    def db_conf(self, value):
        '''
        :param dict value: the update dictionary

        We accecpt a subset of value with following schema::

            {
                'type': str,
                'url': str,
                'host': str,
                'port': int,
                'user': str,
                'passwd': str,
            }

        :raise ValueError: if we get any invalid key.
        :raise TypeError: if we get wrong type of content.
        '''
        key_set = ('type', 'url', 'host', 'port', 'user', 'passwd')

        for key, val in value.items():
            if key not in key_set:
                raise ValueError('Invalid key: {!r}'.format(key))
            if key != 'port' and not isinstance(val, string_types):
                raise TypeError('{!r} must be a string'.format(key))
            elif key == 'port' and not isinstance(val, int):
                raise TypeError("'port' must be an int")

        self.__db_conf.update(value)

    @property
    def available_protos(self):
        '''
        .. todo::
            should auto-detect the working server
        '''
        return ('mqtt', 'zmq', 'websocket')

    @property
    def feature_cates(self):
        '''
        The list of feature categories

        .. deprecated::
        '''
        return ('sight', 'hearing', 'feeling', 'motion', 'other')

    def __del__(self):
        if self.db.provider and self.db.provider is not None:
            with suppress(Exception):
                self.__db.disconnect()

    @property
    def mqtt_conf(self):
        return self.__mqtt.copy()

    @property
    def ws_conf(self):
        return self.__ws.copy()

    @property
    def logging_level(self):
        if self.debug:
            return logging.DEBUG
        else:
            return logging.INFO

    @property
    def session_id(self):  # read-only
        '''
        For each core server instance
        '''
        return self.__session_id

    @property
    def da_expiration(self):
        return self.__da_expiration

    @da_expiration.setter
    def da_expiration(self, val):
        self.__da_expiration = val

    def read_config(self, path: str):
        if not path or not os.path.isfile(path):
            raise OSError('ini file not found: {}'.format(path))

        c = ConfigParser(interpolation=ExtendedInterpolation())
        c.read(path)

        def set_(obj, c: 'config section', name: 'obj.<name>',
                 parse: 'function' = str, key: 'key in ini' = None):  # noqa: F821
            if key is None:
                key = name

            try:
                if isinstance(obj, dict):
                    opt = obj[name]
                    obj[name] = parse(c.get(key, opt))
                else:
                    opt = getattr(obj, name)
                    setattr(self, name, parse(c.get(key, opt)))

            except (AttributeError, KeyError):
                log.warning('Skip unknown config `{}`'.format(name))

        if 'core' in c:  # `core` section
            s = c['core']
            set_(self, s, 'bind')
            set_(self, s, 'userdir')
            set_(self, s, 'http_port', int, key='http-port')
            set_(self, s, 'da_expiration', int, key='da-expiration')
            self.setup_userdir()

        if 'core-db' in c:
            s = c['core-db']
            set_(self.__db_conf, s, 'type')
            set_(self.__db_conf, s, 'url')
            set_(self.__db_conf, s, 'host')
            set_(self.__db_conf, s, 'port', int)
            set_(self.__db_conf, s, 'user')
            set_(self.__db_conf, s, 'passwd')

        if 'core-mqtt' in c:
            s = c['core-mqtt']
            set_(self.__mqtt, s, 'scheme')
            set_(self.__mqtt, s, 'host')
            set_(self.__mqtt, s, 'port', int)

        if 'core-ws' in c:
            s = c['core-ws']
            set_(self.__ws, s, 'scheme')
            set_(self.__ws, s, 'host')
            set_(self.__ws, s, 'port', int)

        if 'aaa' in c:
            setattr(self, 'enable_mqtt_auth',
                    c.getboolean('aaa', 'enable_mqtt_auth', fallback=False))

        if 'aaa-ec' in c:
            s = dict(c.items('aaa-ec'))
            set_(self, s, 'aaa_token', key='ec-token')


config = Config()
