import logging
import os

from pathlib import Path

from configparser import ConfigParser, ExtendedInterpolation

VERSION = '2.3.3'

IS_DEBUG = True

ROOT_PATH = os.path.realpath(os.path.dirname(__file__))

if os.name.startswith('posix'):
    USER_DIR = os.path.join(os.environ['HOME'], '.iottalk')
elif os.name.startswith('nt'):
    USER_DIR = os.path.join(os.environ['USERPROFILE'], '_iottalk')
else:
    raise OSError('Unsupport os type "{}"'.format(os.name))


def _get_db_url(dir_):
    return 'sqlite+pysqlite:///{}'.format(os.path.join(dir_, 'iottalk-gui.db'))


DB_URL = _get_db_url(USER_DIR)
DB_POOL_RECYCLE = 600

LOG_PATH = os.path.join(USER_DIR, 'log')

FLASK_SECRET_KEY = ''
WEB_DA_DIR_PATH = os.path.join(ROOT_PATH, 'da')

AA_HOST = 'localhost'
AA_PORT = '5566'
CCM_HOST = '0.0.0.0'
CCM_PORT = 7788
EC_ENDPOINT = 'http://localhost:9992'
AA_TOKEN = ''
ENABLE_MQTT_AUTH = False

MDB_ACCOUNT = 'iottalk'
MDB_KEY = 'zysomentionsuroppostreye'
MDB_PASS = '917cd9025d2b18056cd0d61657f65fc372e33d25'
MDB_TABLE_FEATURE = 'device_feature'

SMS_SERVER_IP = '202.39.54.130'
SMS_SERVER_LOGIN = '89945934'
SMS_SERVER_PWD = '46804706'
DA_DOWNLOAD_PATH = '\nhttp://pcs.csie.nctu.edu.tw/da/{0}.zip\n'

SESSION_TIME_OUT = 10080  # minutes

GUNICORN_PID_FILE_NAME = str(Path(USER_DIR) / 'gunicorn_pidfile')


class MQTTConfig:
    scheme = 'mqtt'
    host = 'localhost'
    port = 1883
    websocket_scheme = 'ws'
    websocket_port = 1884
    device_req_topic = 'iottalk/api/req/ccm/device'
    device_res_topic = 'iottalk/api/res/ccm/device'
    graph_req_topic = 'iottalk/api/req/ccm/graph/{}'
    graph_res_topic = 'iottalk/api/res/ccm/graph/{}'
    gui_req_topic = 'iottalk/api/gui/req/{}'
    gui_res_topic = 'iottalk/api/gui/res/{}'
    csm_host = host
    csm_port = 9992


MQTT = MQTTConfig()

TYPE_LIST = ['int', 'float', 'boolean', 'void', 'string', 'json']

LOG_COLOR_DEFAULT = '\033[0m'
LOG_LEVEL_GUI = logging.INFO
LOG_COLOR_GUI = '\033[1;35m'
LOG_LEVEL_DEVICE = logging.DEBUG
LOG_COLOR_DEVICE = '\033[1;34m'
LOG_LEVEL_GRAPH = logging.DEBUG
LOG_COLOR_GRAPH = '\033[1;33m'
LOG_LEVEL_SIM = logging.DEBUG
LOG_COLOR_SIM = '\033[1;36m'

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# indicate after `n` seconds, device ownership become public
OWNERSHIP_TIMEOUT = 180

# support output device single bind (by YB)
ODF_SINGLE_BIND = False

# use SimTalk as simulation if endpoint given,
# or use IoTtalk basic simulation if empty string.
SIMTALK_ENDPOINT = ''

SAGEN_ENDPOINT = ''

# other subsystems
AITALK_ENDPOINTS = {'gui': '', 'da': ''}
DATATALK_ENDPOINTS = {'gui': '', 'da': ''}

# OAuth 2.0 Client ID
OAUTH2_CLIENT_ID = ""
# OAuth 2.0 Client Secret
OAUTH2_CLIENT_SECRET = ""
# OAuth 2.0 Redirect URI
OAUTH2_REDIRECT_URI = ""
# OpenID Connect Discovery Endpoint
OIDC_DISCOVERY_ENDPOINT = ""
# OAuth 2.0 Revocation Endpoint
OAUTH2_REVOCATION_ENDPOINT = ""
# Oauth 2.0 Introspect Token Endpoint
OAUTH2_INTROSPECT_ENDPOINT = ""


def read_config(path: str):
    if not path or not os.path.isfile(path):
        raise OSError('ini file not found: {}'.format(path))

    # private logger in this function
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("config")
    mod = globals()
    c = ConfigParser(interpolation=ExtendedInterpolation())
    c.read(path)

    def set_(c: ConfigParser, key: 'key from ini', name: 'var name in config.py',
             parser=str):
        if name not in mod:
            log.warning('variable `%s` unknown', name)
            return
        if key not in c:  # in case of not set in ini
            return

        v = parser(c[key])
        mod[name] = v

    def set_mqtt(c: ConfigParser, m: MQTTConfig, key: 'key from ini',
                 name: 'var name in config.py', parser=str):
        if name not in dir(m):
            log.warning('variable `%s` unknown', name)
            return
        if key not in c:  # in case of not set in ini
            return

        v = parser(c[key])
        setattr(m, name, v)

    def parse_bool(x: str):
        if x in ('1', 'True', 'true'):
            return True
        elif x in ('0', 'false', 'False'):
            return False

        raise ValueError('invalid boolean value "{}"'.format(x))

    def parse_log_level(x: str):
        return getattr(logging, x.upper())

    def parse_log_color(x: str):
        color_map = {
            'default': '\033[0m',
            'black': '\033[30m',
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[37m',
            'brightblack': '\033[1;30m',
            'brightred': '\033[1;31m',
            'brightgreen': '\033[1;32m',
            'brightyellow': '\033[1;33m',
            'brightblue': '\033[1;34m',
            'brightmagenta': '\033[1;35m',
            'brightcyan': '\033[1;36m',
            'brightwhite': '\033[1;37m'
        }
        ret = color_map.get(x.lower())
        if ret is None:
            raise ValueError("invalid color: {}".format(x))
        return ret

    def mkdir(p: os.path, info: str):
        '''
        Create dir if not exists.

        :param info: only use for logging display
        '''
        if os.path.exists(p):
            return
        log.info("create %s dir: %s", info, p)
        return os.mkdir(p)

    if 'gui' in c:
        s = c['gui']
        set_(s, 'debug', 'IS_DEBUG', parse_bool)
        set_(s, 'rootdir', 'ROOT_PATH')
        set_(s, 'userdir', 'USER_DIR')

        # re-redner DB_URL
        mod['DB_URL'] = _get_db_url(mod['USER_DIR'])
        # re-redner LOG_PATH
        mod['LOG_PATH'] = os.path.join(mod['USER_DIR'], 'log')

        set_(s, 'logdir', 'LOG_PATH')
        set_(s, 'web-da-dir', 'WEB_DA_DIR_PATH')
        set_(s, 'flask-secret-key', 'FLASK_SECRET_KEY')
        set_(s, 'bind', 'CCM_HOST')
        set_(s, 'port', 'CCM_PORT', int)
        set_(s, 'session-timeout', 'SESSION_TIME_OUT', int)
        set_(s, 'ownership-timeout', 'OWNERSHIP_TIMEOUT', int)
        set_(s, 'odf-single-bind', 'ODF_SINGLE_BIND', parse_bool)

        # create dirs if not exists
        mkdir(mod['USER_DIR'], 'user')
        mkdir(mod['LOG_PATH'], 'log')

    if 'gui-db' in c:
        s = c['gui-db']
        set_(s, 'url', 'DB_URL')
        set_(s, 'pool-recycle', 'DB_POOL_RECYCLE', int)
        set_(s, 'redis-host', 'REDIS_HOST')
        set_(s, 'redis-port', 'REDIS_PORT', int)

    if 'gui-mqtt' in c:
        s = c['gui-mqtt']
        set_mqtt(s, MQTT, 'scheme', 'scheme')
        set_mqtt(s, MQTT, 'host', 'host')
        set_mqtt(s, MQTT, 'port', 'port', int)
        set_mqtt(s, MQTT, 'csm-host', 'csm_host')
        set_mqtt(s, MQTT, 'csm-port', 'csm_port', int)

        for topic in ('device', 'graph', 'gui'):
            set_mqtt(s, MQTT,
                     '{}-req-topic'.format(topic),
                     '{}_req_topic'.format(topic))
            set_mqtt(s, MQTT,
                     '{}-res-topic'.format(topic),
                     '{}_res_topic'.format(topic))

    if 'gui-ws' in c:
        s = c['gui-ws']
        set_mqtt(s, MQTT, 'scheme', 'websocket_scheme')
        set_mqtt(s, MQTT, 'port', 'websocket_port', int)
        # TODO: support websocket broker host

    if 'gui-log' in c:
        s = c['gui-log']
        set_(s, 'level-gui', 'LOG_LEVEL_GUI', parse_log_level)
        set_(s, 'color-gui', 'LOG_COLOR_GUI', parse_log_color)
        set_(s, 'level-device', 'LOG_LEVEL_DEVICE', parse_log_level)
        set_(s, 'color-device', 'LOG_COLOR_DEVICE', parse_log_color)
        set_(s, 'level-graph', 'LOG_LEVEL_GRAPH', parse_log_level)
        set_(s, 'color-graph', 'LOG_COLOR_GRAPH', parse_log_color)
        set_(s, 'level-sim', 'LOG_LEVEL_SIM', parse_log_level)
        set_(s, 'color-sim', 'LOG_COLOR_SIM', parse_log_color)

    if c.has_section('gui-ec'):
        s = dict(c.items('gui-ec'))
        set_(s, 'ec-endpoint', 'EC_ENDPOINT')

    if c.has_section('aa'):
        mod['ENABLE_MQTT_AUTH'] = c.getboolean('aa', 'enable_mqtt_auth', fallback=False)

    if c.has_section('aa-ccm'):
        s = dict(c.items('aa-ccm'))
        set_(s, 'ccm-token', 'AA_TOKEN')

    if c.has_section('aa-zmq-frontend'):
        s = dict(c.items('aa-zmq-frontend'))
        set_(s, 'host', 'AA_HOST')
        set_(s, 'port', 'AA_PORT')

    if c.has_section('gui-simtalk'):
        s = dict(c.items('gui-simtalk'))
        set_(s, 'simtalk-endpoint', 'SIMTALK_ENDPOINT')

    if c.has_section('gui-sagen'):
        s = dict(c.items('gui-sagen'))
        set_(s, 'sagen-endpoint', 'SAGEN_ENDPOINT')

    if 'subsystems' in c:
        s = c['subsystems']

        def parser(s: str):
            ls = s.split(' ')
            assert len(ls) == 2
            return {'gui': ls[0], 'da': ls[1]}

        set_(s, 'aitalk-endpoints', 'AITALK_ENDPOINTS', parser=parser)
        set_(s, 'datatalk-endpoints', 'DATATALK_ENDPOINTS', parser=parser)

    if c.has_section('gui-oauth2'):
        s = dict(c.items('gui-oauth2'))
        set_(s, 'client-id', 'OAUTH2_CLIENT_ID')
        set_(s, 'client-secret', 'OAUTH2_CLIENT_SECRET')
        set_(s, 'redirect-uri', 'OAUTH2_REDIRECT_URI')
        set_(s, 'oidc-discovery-endpoint', 'OIDC_DISCOVERY_ENDPOINT')
        set_(s, 'revocation-endpoint', 'OAUTH2_REVOCATION_ENDPOINT')
        set_(s, 'introspect-endpoint', 'OAUTH2_INTROSPECT_ENDPOINT')
