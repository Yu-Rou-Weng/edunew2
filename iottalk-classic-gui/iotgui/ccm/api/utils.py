import logging
import os
import typing

import flask_login

from functools import wraps

from flask import Blueprint
from flask import jsonify
from flask import session as http_session

from iotgui import config
from iotgui.ccm.api.const import APIResponse
from iotgui.ccm.modules.utils import CCMError, Context
from iotgui.ccm.mqttclient import mqtt_module
from iotgui.db import session_scope

log = logging.getLogger("{}ccm.api.utils\033[0m".format(config.LOG_COLOR_GUI))


def invalid_input(x: dict, required: dict, optional: dict = {}):
    '''
    Check the required field in the given json input,
    If invalid, returns the error message.
    If valid, returns empty string.

    :param dict: a dictionary comes from requests.json
    :param required: a dictionary contains the required field and its type::

        {
            'field1': str,
            'field2': int,
            'field3': (int, type(None)),  // tuple only, list is not allowed
            ...
        }

    :param optional: the optional field
    '''
    if x is None:
        return ('Content-type should be `application/json` and '
                'body should not be empty')

    # field existence
    for k in required:
        if k not in x:
            return 'field `{}` is required'.format(k)

    # check unknown keys
    keyset = set(required.keys()).union(optional.keys())
    for k in x.keys():
        if k not in keyset:
            return 'field `{}` unknown'.format(k)

    # check type
    for y in (required, optional):
        for k, types in y.items():
            if k not in x:
                continue

            types = (types,) if not isinstance(types, tuple) else types
            for typ in types:
                if isinstance(x[k], typ):
                    break
            else:
                return 'field `{}` should be type `{}`'.format(k, typ)

    # check str non-empty
    for k, v in x.items():
        if k not in required:  # skip check for optional fields
            continue
        if isinstance(v, str) and not v:
            return 'field `{}` should not be empty'.format(k)

    return ''  # ok


def blueprint(name: __name__, filename: __file__):
    '''
    simple wrapper for creating Blueprint of CCM HTTP APIs.
    '''
    ver = os.path.split(os.path.dirname(filename))[-1]
    bname = '{}_api_{}'.format(name, ver)
    log.debug('create Blueprint %s', bname)
    return Blueprint(bname, name)


def json_error(msg: str, **other) -> jsonify:
    obj = {
        'state': 'error',
        'reason': msg,
    }
    obj.update(other)
    return jsonify(obj)


def api_login_required(f):
    '''
    Decorator for the CCM API that requires login.

    The decorated function will return error message in JSON format and
    HTTP 401 if request is not authenticated.
    '''

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not flask_login.current_user.is_authenticated:
            return json_error('please login first'), 401
        return f(*args, **kwargs)

    return wrapper


def api_admin_required(f):
    '''
    Decorator for the CCM API that requires admin.

    The decorated function will return error message in JSON format and
    HTTP 403 if request is forbidden.
    '''

    @wraps(f)
    def wrapper(*args, **kwargs):
        if flask_login.current_user.is_anonymous or not flask_login.current_user.is_admin:
            return json_error('You are not administrator.'), 403
        return f(*args, **kwargs)

    return wrapper


def apply_op(op: str, *args, post_proc: typing.Callable[[dict], dict] = None,
             status_code=200, error_code=400, **kwargs):
    '''
    Apply opeartion to ``iotgui.ccm.modules.CCMModule``.

    :param error_code: http status code on error

    e.g.
    >>> return apply_op('op_delete_project', pid)
    '''
    ret = APIResponse.OK
    try:
        x = run_op(op, *args, **kwargs)
        if post_proc:
            x = post_proc(x)
        ret.update(x)
    except CCMError as e:
        return json_error(e.msg), error_code

    return jsonify(ret), status_code


def run_op(op: str, *args, **kwargs):
    method = getattr(mqtt_module, op)
    with session_scope() as db_session:
        ctx = Context(http_session['user_id'], db_session)
        return method(ctx, *args, **kwargs)


def wrap_data(x: dict):
    '''wrap a dictionary into field ``data``'''
    return {'data': x}
