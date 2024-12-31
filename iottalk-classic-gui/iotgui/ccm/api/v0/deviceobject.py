import logging

from flask import request
from flask import session as http_session

from iotgui import config
from iotgui.ccm.modules import CCMModule
from iotgui.ccm.modules.utils import CCMError, Context
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data
from iotgui.db import session_scope

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/', methods=['PUT'], strict_slashes=False)
@api_login_required
def create(pid):
    '''
    Request::

        {
            'dm_id': 42,  // Device Model id
            'df': [  // list of Device Feature id
                123,
                ...
            ],
        }

    Response::

        {
            'state': 'ok',
            'do_id': 42,
        }

    Response error if Device Model or Device Feature not found::

        {
            'state': 'error',
            'reason': '... not found',
        }
    '''
    err = invalid_input(request.json, {'dm_id': int, 'df': list})
    if err:
        return json_error(err), 400

    try:
        df_names = map_df_names(request.json['df'])
    except CCMError as e:
        return json_error(e.msg), 404

    return apply_op('op_create_device_object', pid, request.json['dm_id'],
                    df_names, status_code=201, error_code=404)


def map_df_names(df_ids):
    # FIXME: op_create_device_object should accept list of df id not df names
    #        but we convert it in this route as a workaround.
    #        We should change the interface of op_create_device_object someday
    m = CCMModule()

    def f(df_id):
        with session_scope() as db_session:
            ctx = Context(http_session['user_id'], db_session)
            return m.op_get_device_feature_info(ctx, df_id)['df_name']

    return list(map(f, df_ids))


@api.route('/<int:do_id>/', methods=['GET'], strict_slashes=False)
@api_login_required
def info(pid, do_id):
    '''
    Response::

        {
            'state': 'ok',
            'data': {
                'do': {
                    'do_id': 24,
                    'dfo': [...],
                },
                'dm_id': 42,
                'dm_name': 'FooModel',
                'dm_type': 'other',
                'df_list': [...],
            },
        }
    '''
    return apply_op('op_get_device_object_info', do_id, pid, post_proc=wrap_data,
                    error_code=404)


@api.route('/<int:do_id>/', methods=['POST'], strict_slashes=False)
@api_login_required
def update(pid, do_id):
    '''
    Update Device Object feature list

    Request::

        {
            'df': [
                ...  // list of Device Feature names
            ]
        }

    Response::

        {
            'state': 'ok',
            'do_id': 42,
        }
    '''
    err = invalid_input(request.json, {'df': list})
    if err:
        return json_error(err), 400

    try:
        df_names = map_df_names(request.json['df'])
    except CCMError as e:
        return json_error(e.msg), 404

    return apply_op('op_update_device_object', do_id, pid, df_names,
                    error_code=404)


@api.route('/<int:do_id>/', methods=['DELETE'], strict_slashes=False)
@api_login_required
def delete(pid, do_id):
    '''
    Response::

        {
            'state': 'ok',
            'do_id': 42,
        }

    Response error if not found::

        {
            'state': 'error',
            'reason': 'Device Object 42 not found',
        }
    '''
    return apply_op('op_delete_device_object', do_id, error_code=404)
