import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data, run_op

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/', methods=['PUT'], strict_slashes=False)
@api_login_required
def create():
    '''
    Request::

        {
            'dm_name': 'Foo',
            'df_list': [
                {
                    'df_id': 12,  // required
                    'df_parameter': [{}, ...]  // required
                    'tags': [],  // optional
                },
                ...
            ],
            'dm_type': 'other',  // optional
            'plural': False, // optional
            'device_only': False //optional
        }

    Response::

        {
            'state': 'ok',
            'dm_id': 42,
        }

    Response if name already exists with HTTP code 400::

        {
            'state': 'error',
            'reason': 'Device Model "..." already exists',
        }

    Example::

        {
            "dm_name": "FooModel",
            "df_list": [
                {
                    "df_id": 12,
                    "df_parameter": [{}]
                }
            ]
        }
    '''
    err = check_dm_format(request.json)
    if err:
        return err
    return apply_op('op_create_device_model', **request.json, status_code=201)


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def list_():
    '''
    Response::

        {
            'state': 'ok',
            'data': [
                // Device Model without Device Feature info
            ],
        }
    '''
    def f(x):
        return {'data': x['dm_list']}

    return apply_op('op_get_device_model_list', post_proc=f)


@api.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@api_login_required
def model_info(id_):
    '''
    Response::

        {
            'state': 'ok',
            'data': {
                'dm_id': 42,
                'dm_name': 'FooModel',
                'df_list': [...]
                'dm_type': 'other',
                'plural': False,
                'device_only': False
            },
        }

    Response if id not found with HTTP code 404::

        {
            'state': 'error',
            'reason': 'Device Model id "42" not found',
        }
    '''
    return apply_op('op_get_device_model_info', id_, post_proc=wrap_data,
                    error_code=404)


@api.route('/<string:name>', methods=['GET'], strict_slashes=False)
@api_login_required
def model_info_by_name(name):
    return apply_op('op_get_device_model_info',
                    run_op('op_search_device_model', name),
                    post_proc=wrap_data, error_code=404)


@api.route('/<int:id_>', methods=['POST'], strict_slashes=False)
@api_login_required
def model_update(id_):
    '''
    Request::

        {
            'dm_name': 'name',  // immutable, only for verifying
            'df_list': [...],
            'dm_type': 'other',  // optional
            'plural': False, // optional
            'device_only': False //optional
        }

    Response::

        {
            'state': 'ok',
            'dm_id': 42,
        }
    '''
    err = check_dm_format(request.json)
    if err:
        return err
    return apply_op('op_update_device_model', id_, **request.json)


@api.route('/<int:id_>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def model_delete(id_):
    '''
    Response::

        {
            'state': 'ok',
            'dm_id': 42,
        }
    '''
    return apply_op('op_delete_device_model', id_, error_code=404)


@api.route('/<string:name>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def model_delete_by_name(name):
    return apply_op('op_delete_device_model',
                    run_op('op_search_device_model', name),
                    error_code=404)


def check_dm_format(data):
    '''
    check device model format
    '''
    err = invalid_input(data,
                        {'dm_name': str, 'df_list': list}, {'dm_type': str})
    if err:
        return json_error(err), 400

    for x in data['df_list']:
        err = invalid_input(
            x,
            {'df_id': int, 'df_parameter': list},
            {'tags': list, 'df_category': str, 'df_name': str, 'df_type': str,
             'comment': str, 'param_no': int})
        if err:
            return json_error(err), 400

    # correct df_id in df_parameter
    for x in data['df_list']:
        df_id = x['df_id']
        for y in x['df_parameter']:
            y['df_id'] = df_id

    return None
