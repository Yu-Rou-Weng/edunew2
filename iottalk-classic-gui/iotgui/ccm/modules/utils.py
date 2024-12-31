"""Something useful function."""
import datetime
import json
import sys
import traceback

from contextlib import contextmanager

from iotgui.config import LOG_COLOR_DEFAULT


class Context:
    def __init__(self, u_id, db_session, client_id=None):
        self.u_id = u_id
        self.db_session = db_session
        self.client_id = client_id  # mqtt client topic uuid


class CCMError(Exception):
    """For CCM to raise module Exception."""

    def __init__(self, msg):
        """Initial Function.

        :param msg: exception msg.
        """
        self.msg = msg

    def __str__(self):
        """
        String format function.

        :return: '[CCMError] {msg}'
        """
        return '[CCMError] {}'.format(repr(self.msg))


class ComplexEncoder(json.JSONEncoder):
    """
    Support json dump datetime.

    Usage:
        json.dumps({'now':now}, cls=ComplexEncoder)
    """

    def default(self, obj):
        """
        Overwrite json.JSONEncoder.default.

        :return: if obj is datetime or date, return string format time.
        """
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


def record_parser(row, str_datetime=True):
    """Convert query object by sqlalchemy to dictionary object."""
    if not row:
        return None

    d = {}
    if hasattr(row, '__table__'):
        for column in row.__table__.columns:
            d[column.name] = getattr(row, column.name)
            if str_datetime and isinstance(d[column.name], datetime.datetime):
                d[column.name] = str(d[column.name])
    if hasattr(row, '_fields'):
        for column_name in row._fields:
            d[column_name] = getattr(row, column_name)
            if str_datetime and isinstance(d[column_name], datetime.datetime):
                d[column_name] = str(d[column_name])
    return d


def color_wrapper(text, color=LOG_COLOR_DEFAULT):
    return '{}{}{}'.format(color, text, LOG_COLOR_DEFAULT)


@contextmanager
def suppress(*args):
    """
    Inspire by py34+, contextlib.suppress.

    >>> with suppress(OSError):
    ...     raise OSError()

    >>> with suppress(OSError, KeyboardInterrupt):
    ...     raise KeyboardInterrupt()
    """
    try:
        yield
    except args:
        pass


def showtrace(sig, frame):
    '''
    this is useful
    >>> import signal
    >>> signal.signal(signal.SIGUSR1, showtrace)
    '''
    message = 'Signal received : \nTraceback:\n'
    message += ''.join(traceback.format_stack(frame))
    print(message)
    for thread_id, frame in sys._current_frames().items():
        message = 'Signal received : \nTraceback:\n'
        message += ''.join(traceback.format_stack(frame))
        print(message)


def mqtt_server_thread(f):
    '''
    Guard for MQTT server thread.

    TODO: accept logger as param
    '''

    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            traceback.print_exc()

    return wrapper
