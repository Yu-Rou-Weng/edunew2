'''
The configuration system.

This module will export a singleton of ``Config`` -- ``config``.
'''
import logging
import os

from configparser import ConfigParser, ExtendedInterpolation
from six import string_types

from flask_sqlalchemy import SQLAlchemy

__all__ = ('config',)

log = logging.getLogger('iottalk.config')


class Config(object):
    '''
    Main configuration here.

    If a property consider as *readonly*, we will use ``property`` decorator
    for it.

    This class is responsible to setup user config dir.
    On Unix, we will have ``$HOME/.edutalk``;
    '''

    __http_port = 7000
    __bind = '0.0.0.0'
    __debug = False
    __db_conf = {
        'type': 'sqlite',  # or `mysql`
        'url': 'edutalk.db',
        'host': 'localhost',
        'port': -1,
        'user': '',
        'passwd': '',
    }
    __csm_api = 'http://localhost:9992'
    __ag_url = 'http://localhost:9000'
    __secret_key = ''
    __web_server_prefix = ''
    __proxy_used = ''
    __client_id = ''
    __client_secret = ''
    __redirect_uri = ''
    __discovery_endpoint = ''
    __authorization_endpoint = ''
    __token_endpoint = ''
    __revocation_endpoint = ''
    __account_host = ''
    __db = None
    __userdir = ''
    __deeplink = 'https://iottalk.github.io/applink/edutalk'  # default
    __kurento_server_url = 'wss://hi1.iottalk.tw:8433/kurento'  # default
    __app = None
    __admin_username = ''
    __admin_sub = ''
    __admin_email = ''
    __aaa_api_token = ''
    __register_need_approve = True
    __new_admin = None
    __es_password = ''

    def __init__(self):
        self.setup_userdir()

    @property
    def userdir(self):
        if self.__userdir:
            return self.__userdir

        if os.name.startswith('posix'):
            self.__userdir = os.path.join(os.environ['HOME'], '.edutalk')
        else:
            raise OSError('Unsupport os type "{}"'.format(os.name))

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
    def bind(self):
        return self.__bind

    @bind.setter
    def bind(self, val):
        self.__bind = val

    @property
    def http_port(self):
        return self.__http_port

    @http_port.setter
    def http_port(self, val):
        self.__http_port = val

    @property
    def debug(self):
        return self.__debug

    @debug.setter
    def debug(self, val: int):
        self.__debug = val = bool(val)
        # logging
        logging.basicConfig(level=logging.DEBUG if val else logging.INFO)

    @property
    def deeplink(self):
        return self.__deeplink

    @deeplink.setter
    def deeplink(self, val):
        self.__deeplink = val

    @property
    def kurento_server_url(self):
        return self.__kurento_server_url

    @kurento_server_url.setter
    def kurento_server_url(self, val):
        self.__kurento_server_url = val

    @property
    def db(self):
        '''
        :return: The pony orm db instance without db provider binding
        '''
        if self.__db:
            return self.__db

        self.__db = SQLAlchemy()
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
    def app(self):
        '''
        The Flask app instance
        '''
        return self.__app

    @app.setter
    def app(self, val):
        '''
        Init the database for the app while setting
        '''
        self.__app = val
        self.db.init_app(self.app)

    @property
    def csm_api(self):
        return self.__csm_api

    @csm_api.setter
    def csm_api(self, val):
        val = val[:-1] if val.endswith('/') else val
        self.__csm_api = val

    @property
    def ag_url(self):
        '''
        IoTtalk CCM API URL
        '''
        return self.__ag_url

    @ag_url.setter
    def ag_url(self, val):
        val = val[:-1] if val.endswith('/') else val
        self.__ag_url = val

    def csm_url(self, path: str = ''):
        url = '{}/{}'.format(self.csm_api, path)
        return url[:-1] if url.endswith('/') else url

    @property
    def secret_key(self):
        '''
        Flask secret key
        '''
        return self.__secret_key

    @secret_key.setter
    def secret_key(self, val):
        self.__secret_key = val

    @property
    def web_server_prefix(self):
        return self.__web_server_prefix

    @web_server_prefix.setter
    def web_server_prefix(self, val):
        self.__web_server_prefix = val

    @property
    def proxy_used(self):
        return self.__proxy_used

    @proxy_used.setter
    def proxy_used(self, val):
        self.__proxy_used = val

    @property
    def client_id(self):
        '''
        OAuth 2.0 Client ID
        '''
        return self.__client_id

    @client_id.setter
    def client_id(self, val):
        self.__client_id = val

    @property
    def client_secret(self):
        '''
        OAuth 2.0 Client Secret
        '''
        return self.__client_secret

    @client_secret.setter
    def client_secret(self, val):
        self.__client_secret = val

    @property
    def redirect_uri(self):
        '''
        OAuth 2.0 Redirect URI
        '''
        return self.__redirect_uri

    @redirect_uri.setter
    def redirect_uri(self, val):
        self.__redirect_uri = val

    @property
    def discovery_endpoint(self):
        '''
        OpenID Connect Discovery Endpoint
        '''
        return self.__discovery_endpoint

    @discovery_endpoint.setter
    def discovery_endpoint(self, val):
        self.__discovery_endpoint = val

    @property
    def token_endpoint(self):
        '''
        OAuth 2.0 Token Endpoint
        '''
        return self.__token_endpoint

    @token_endpoint.setter
    def token_endpoint(self, val):
        self.__token_endpoint = val

    @property
    def authorization_endpoint(self):
        '''
        OAuth 2.0 Authorization Endpoint
        '''
        return self.__authorization_endpoint

    @authorization_endpoint.setter
    def authorization_endpoint(self, val):
        self.__authorization_endpoint = val

    @property
    def revocation_endpoint(self):
        '''
        OAuth 2.0 Revocation Endpoint
        '''
        return self.__revocation_endpoint

    @revocation_endpoint.setter
    def revocation_endpoint(self, val):
        self.__revocation_endpoint = val

    @property
    def account_host(self):
        return self.__account_host

    @account_host.setter
    def account_host(self, val):
        self.__account_host = val

    @property
    def admin_username(self):
        '''
        Username of administrator in profile
        '''
        return self.__admin_username

    @admin_username.setter
    def admin_username(self, val):
        self.__admin_username = val

    @property
    def admin_sub(self):
        '''
        ID of administrator in profile
        '''
        return self.__admin_sub

    @admin_sub.setter
    def admin_sub(self, val):
        self.__admin_sub = val

    @property
    def admin_email(self):
        '''
        E-mail of administrator in profile
        '''
        return self.__admin_email

    @admin_email.setter
    def admin_email(self, val):
        self.__admin_email = val

    @property
    def aaa_api_token(self):
        return self.__aaa_api_token

    @aaa_api_token.setter
    def aaa_api_token(self, val):
        self.__aaa_api_token = val

    @property
    def register_need_approve(self):
        return self.__register_need_approve

    @register_need_approve.setter
    def register_need_approve(self, val):
        self.__register_need_approve = eval(val)

    @property
    def new_admin(self):
        '''
        The user who is changed to the admin
        '''
        return self.__new_admin

    @new_admin.setter
    def new_admin(self, val):
        self.__new_admin = val

    @property
    def es_password(self):
        '''
        elastic's password in ElasticSearch.
        '''
        return self.__es_password

    @es_password.setter
    def es_password(self, val):
        self.__es_password = val

    def read_config(self, path):
        if not path:
            return

        c = ConfigParser(interpolation=ExtendedInterpolation())
        c.read(path)

        def set_(obj, c, name, parse=str):
            '''
            c: config section
            parse: function
            '''
            try:
                if isinstance(obj, dict):
                    opt = obj[name]
                    obj[name] = parse(c.get(name, opt))
                else:
                    opt = getattr(obj, name)
                    setattr(self, name, parse(c.get(name, opt)))

            except (AttributeError, KeyError):
                log.warning('Skip unknown config `{}`'.format(name))

        if 'edutalk' in c:  # `edutalk` section
            s = c['edutalk']
            set_(self, s, 'debug', int)
            set_(self, s, 'bind')
            set_(self, s, 'userdir')
            set_(self, s, 'http_port', int)
            set_(self, s, 'secret_key')
            set_(self, s, 'web_server_prefix')
            set_(self, s, 'deeplink')
            set_(self, s, 'kurento_server_url')
            set_(self, s, 'admin_username')
            set_(self, s, 'admin_sub')
            set_(self, s, 'admin_email')
            set_(self, s, 'aaa_api_token')
            set_(self, s, 'register_need_approve')

        if 'edutalk-db' in c:
            s = c['edutalk-db']
            set_(self.__db_conf, s, 'type')
            set_(self.__db_conf, s, 'url')
            set_(self.__db_conf, s, 'host')
            set_(self.__db_conf, s, 'port', int)
            set_(self.__db_conf, s, 'user')
            set_(self.__db_conf, s, 'passwd')

        if 'iottalk' in c:
            s = c['iottalk']
            set_(self, s, 'csm_api')
            set_(self, s, 'ag_url')

        if 'oauth2' in c:
            s = c['oauth2']
            set_(self, s, 'proxy_used')
            set_(self, s, 'client_id')
            set_(self, s, 'client_secret')
            set_(self, s, 'redirect_uri')
            set_(self, s, 'discovery_endpoint')
            set_(self, s, 'authorization_endpoint')
            set_(self, s, 'token_endpoint')
            set_(self, s, 'revocation_endpoint')
            set_(self, s, 'account_host')

        if 'elasticsearch' in c:
            s = c['elasticsearch']
            set_(self, s, 'es_password')


config = Config()
