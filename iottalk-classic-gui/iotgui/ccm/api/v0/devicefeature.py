import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data, run_op

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))
DF_FORMAT = {
    'required': {
        'df_type': str,
        'df_name': str,
        'df_parameter': list},
    'optional': {
        'comment': str,
        'df_category': str,
    },
}


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def list_():
    '''
    Response::

        {
            'state': 'ok',
            'input': [...],
            'output': [...],
        }
    '''
    return apply_op('op_get_device_feature_list', post_proc=wrap_data)


@api.route('/', methods=['PUT'], strict_slashes=False)
@api_login_required
def create():
    '''
    Request::

        {
            "df_type": "input|output",
            "df_name": "Foo",
            "df_parameter": [
                {
                    "max": 1.0,  // optional
                    "min": 0.0,  // optional
                    "param_type": "float",
                },
                ...
            ],
            "comment": "42",  // optional
            "df_category": "other",  // optional
        }

    Response::

        {
            'state': 'ok',
            'df_id': 42,
        }
    '''
    err = invalid_input(request.json, **DF_FORMAT)
    if err:
        return json_error(err), 400
    return apply_op('op_create_device_feature', **request.json, status_code=201)


@api.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@api_login_required
def feature_get(id_):
    '''
    Response::

        {
            'state': 'ok',
            'data': {
                ...
            },
        }
    '''
    return apply_op('op_get_device_feature_info', id_, post_proc=wrap_data,
                    error_code=404)


@api.route('/<string:name>', methods=['GET'], strict_slashes=False)
@api_login_required
def feature_get_by_name(name):
    return apply_op('op_get_device_feature_info',
                    run_op('op_search_device_feature', name),
                    post_proc=wrap_data, error_code=404)


@api.route('/<int:id_>', methods=['POST'], strict_slashes=False)
@api_login_required
def feature_post(id_):
    '''
    Request format is same as ``update``

    Response::

        {
            'state': 'ok',
            'df_id': 42,
        }

    Response if the id not found::

        {
            'state': 'error',
            'reason': 'Device Feature not found',
        }
    '''
    err = invalid_input(request.json, **DF_FORMAT)
    if err:
        return json_error(err), 400

    # insert ``df_id`` into ``df_parameter``
    for i in request.json['df_parameter']:
        i['df_id'] = id_

    return apply_op('op_update_device_feature', id_, **request.json,
                    error_code=404)


@api.route('/<int:id_>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def feature_delete(id_):
    '''
    Response::

        {
            'state': 'ok',
            'df_id': 42,
        }
    '''
    return apply_op('op_delete_device_feature', id_, error_code=404)


@api.route('/<string:name>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def feature_delete_by_name(name):
    return apply_op('op_delete_device_feature',
                    run_op('op_search_device_feature', name),
                    error_code=404)
