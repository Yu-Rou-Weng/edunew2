"""
DB Module.

Usage example:
    from iotgui import db
    from iotgui.db.model import Project

    db.connect()
    s = db.get_session()
    p = s.query(Project).all()
"""
import os
import pkg_resources
import subprocess

from contextlib import contextmanager
from time import sleep


from sqlalchemy import create_engine
from sqlalchemy import exc
from sqlalchemy.orm import Session

from iotgui import config
from iotgui.config import DB_POOL_RECYCLE

DB_FILE = config.DB_URL.split('///')[-1]
engine = None


def check_connection(max_retry=5):
    """
    check db connect

    :param max_retry: Maximum reconnection db times.

    if failed, it will retry at most ``max_retry`` times and
    the waiting interval between retries is determined by the exponential backoff,
    ``min(2 ** times, 10)``.
    """
    reconnect_time = 0
    last_exception = None
    while reconnect_time < max_retry:
        try:
            engine = create_engine(config.DB_URL, pool_recycle=DB_POOL_RECYCLE)
            con = engine.connect()
            con.close()
        except exc.OperationalError as e:
            last_exception = e
            print("Connect to db failed")
        except Exception as e:
            last_exception = e
            print("Unknown error: {}".format(e))
        else:
            print("Connect db successful")
            return
        finally:
            engine.dispose()
        sleep_time = min(2 ** reconnect_time, 10)
        print("retried {} time(s), waiting {} sec for next retry".format(
            reconnect_time + 1, sleep_time))
        reconnect_time += 1
        sleep(sleep_time)
    raise last_exception


def is_sqlite(url: str):
    return url.startswith('sqlite')


def insert_default():
    """Import default db_const for IoTtalk."""
    connect()
    default_file = pkg_resources.resource_filename('iotgui', 'db/db_const.json')

    with open(default_file, 'r') as f:
        import json
        from iotgui.db.import_ import import_data
        import_data(json.load(f))


def connect():
    """Connect to db, should be call before get_session()."""
    check_connection()

    global engine

    if engine:
        return

    engine = create_engine(config.DB_URL, pool_recycle=DB_POOL_RECYCLE)


def create():
    """Create new database file."""
    print('Creating new database ...')
    migrate()
    insert_default()


def migrate():
    """Database migration."""
    check_connection()

    # Get alembic.ini through pkg_resources API
    alembic_ini_path = pkg_resources.resource_filename('iotgui', 'alembic/alembic.ini')

    subprocess.run(
        ['alembic', '-c', str(alembic_ini_path),
         '-x', 'db_url={}'.format(config.DB_URL),
         'upgrade', 'head']
    )


def get_session():
    """Get db connect session to execute sql."""
    if not engine:
        raise Exception('You should invoke connect() first.')
    return Session(engine)


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.

    Ref: https://bit.ly/2FEbwP2
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset():
    """Reset(Init) db."""
    if is_sqlite(config.DB_URL):
        print('Deleting old database ...')
        file_name = DB_FILE

        if os.path.isfile(DB_FILE):
            os.remove(file_name)

        create()
    else:  # in case of MySQL/MariaDB
        create()
