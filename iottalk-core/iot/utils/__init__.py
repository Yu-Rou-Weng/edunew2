import json
import logging
import os
import six

from contextlib import contextmanager
from threading import Lock as _Lock

from pony.orm import db_session

from iot.const import FIXTURES_DIR

try:
    from json import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

log = logging.getLogger('iottalk')


def is_posix():
    return os.name.startswith('posix')


def is_win():
    return os.name.startswith('nt')


@contextmanager
def suppress(*args):
    '''
    Inspire by py34+, contextlib.suppress

    >>> with suppress(OSError):
    ...     raise OSError()

    >>> with suppress(OSError, KeyboardInterrupt):
    ...     raise KeyboardInterrupt()
    '''
    try:
        yield
    except args:
        pass


def load_json_from_file(filename):
    '''
    :return: the json decoded object if load successfully.
             None if loading failed
    '''
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except ValueError as err:
            log.error('Loading fixture {!r} failed', *err.args)


def load_fixtures(fixtures, db):
    '''
    Load all fixtures to db from the given file list.

    The fixture is an json file contain some db records.
    It should have following schema::

        {
            'table_name': {
                'tuple_primary_key1': {
                    'field 1': '...',
                    'field 2': '...'
                }
            }
        }

    :param fixtures: the file name list
    :type fixtures: iterable
    :param db: the pony db instance
    '''
    for filename in fixtures:
        fixture = load_json_from_file(filename)
        if fixture is None:
            continue

        with db_session:
            for table in fixture.keys():
                obj = getattr(db, table, None)
                if obj is None:
                    log.warning('The table {!r} not supported'.format(table))
                    continue

                for id_, attrs in fixture[table].items():
                    obj(id=id_, **attrs)

        log.info('fixture {!r} loaded successfully'.format(filename))


def load_dev_fixtures(db):
    '''
    Load all ``fixtures/dev-*`` into database. We will invoke
    :py:func:`~utils.load_fixtures`.

    :param db: the pony db instance
    '''
    load_fixtures(
        sorted([
            os.path.join(FIXTURES_DIR, f)
            for f in os.listdir(FIXTURES_DIR)
            if os.path.isfile(os.path.join(FIXTURES_DIR, f))
               and f.startswith('dev-')]),
        db)


if six.PY2:
    from Queue import Queue

    class SimpleLock(object):
        def __init__(self):
            self._q = Queue(maxsize=1)
            self._q.put(True)

        def acquire(self, block=True, timeout=None):
            return self._q.get(block, timeout)

        def release(self):
            self._q.put(True)

        def __enter__(self):
            return self.acquire()

        def __exit__(self, exc_type, exc_value, traceback):
            self.release()


else:  # python3+
    SimpleLock = _Lock
