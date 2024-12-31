import logging
import os

from datetime import datetime

from uuid import UUID, uuid4

from pony import orm

from iot.config import config

log = logging.getLogger('iottalk')


def islist(val):
    return isinstance(val, list)


def isdict(val):
    return isinstance(val, dict)


def check_accept_protos(protos):
    '''
    SQL field checker for :py:attr:Resource.accept_protos

    The protos are caser-insensitive.

    :param protos: an string can be decoded as a json list
    :return: ``True``
    :raise ValueError: if there is any unrecognized protocol

    .. todo::
        check the uniqueness

    >>> check_accept_protos(["MQTT", "WebSocket"])
    True
    >>> check_accept_protos(["mqtt", "websocket"])
    True
    '''
    if not isinstance(protos, list):
        return False

    for proto in map(lambda x: x.lower(), protos):
        if proto not in config.available_protos:
            raise ValueError('Invalid protocol: {!r}'.format(proto))
    return True


def define_entities(db):
    '''
    Difine the database entities

    :param db: the pony database instance
    '''
    class Resource(db.Entity):
        id = orm.PrimaryKey(UUID)
        accept_protos = orm.Optional(
            orm.Json, py_check=check_accept_protos, default=[])
        idf_list = orm.Optional(orm.Json, py_check=islist, default=[])
        odf_list = orm.Optional(orm.Json, py_check=islist, default=[])
        name = orm.Optional(str)
        revision = orm.Required(UUID, default=uuid4)
        register_time = orm.Required(datetime, default=datetime.now)
        profile = orm.Optional(orm.Json, py_check=isdict, default={})

        def to_json(self):
            ret = {
                'id': str(self.id),
                'rev': str(self.revision),
                'register_time': self.register_time.timestamp(),
            }
            # Optional fields
            optional = (
                ('name', self.name),
                ('accept_protos', self.accept_protos),
                ('idf_list', self.idf_list),
                ('odf_list', self.odf_list),
                ('profile', self.profile),
            )
            ret.update({k: v for k, v in optional if v})

            return ret


def db_init(db=None):
    '''
    Database init.

    We will create sqlite3 db file in config.userdir, usually at the user
    home dir.

    Also, we will generate mapping for pony orm.

    :param db: the pony database instance. Default is ``config.db``
    '''
    db = db if db else config.db
    if db.provider is not None:
        log.warning('config.db has binded already.')
        return

    db_type = config.db_conf['type']
    if db_type == 'sqlite':
        if config.db_conf['url'] != ':memory:':
            db_path = os.path.join(config.userdir, config.db_conf['url'])
        else:
            db_path = ':memory:'

    define_entities(db)

    if db_type == 'sqlite':
        db.bind('sqlite', db_path, create_db=True)
    elif db_type == 'mysql':
        db.bind('mysql', config.db_conf['host'], config.db_conf['user'],
                config.db_conf['passwd'], db=config.db_conf['url'],
                charset='utf8mb4')

    db.generate_mapping(create_tables=True)
