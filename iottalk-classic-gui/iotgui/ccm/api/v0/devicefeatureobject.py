import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


# @api.route('/', methods=['PUT'], strict_slashes=False)
@api_login_required
def __create(p_id, do_id):
    '''
    Reserved, not public API.

    Request::

        {
            "df_id": 24,
            "alias_name": "good_feature"
        }

    Response::

        {
            'state': 'ok',
            'dfo_id': 42,
        }
    '''
    err = invalid_input(request.json, {'df_id': int,
                                       'alias_name': str})
    if err:
        return json_error(err), 400
    return apply_op('op_create_device_feature_object', do_id, **request.json,
                    status_code=201)


# @api.route('/<int:id_>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def __delete(pid, do_id, id_):
    '''
    Reserved, not public API.

    Response::

        {
            'state': 'ok',
            'do_id': 42,
            'dfo_id': 24
        }
    '''
    err = invalid_input(request.json, {'do_id': int})
    if err:
        return json_error(err), 400
    return apply_op('op_delete_device_feature_object', id_, do_id,
                    error_code=404)


@api.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@api_login_required
def get(pid, do_id, id_):
    '''
    Response::

        {
            'state': 'ok',
            'data': {
                'dfo_id': 42,
                'df_id': 24,
                'df_type': 'input',
                'alias_name': 'good_feature',
                'dm_name': 'good_model',
                'df_mapping_func': [ ...],
                'df_parameter': [ ...]
            },
        }
    '''
    return apply_op('op_get_device_feature_object_info', id_, pid,
                    post_proc=wrap_data, error_code=404)


@api.route('/<int:id_>', methods=['POST'], strict_slashes=False)
@api_login_required
def update(pid, do_id, id_):
    '''
    Request::

        {
            'alias_name': 'Finn',
            'df_parameter': [ { ... }, ... ]
        }

    Response::

        {
            'state': 'ok',
            'dfo_id': 24
        }
    '''
    err = invalid_input(request.json, {'alias_name': str,
                                       'df_parameter': list})
    if err:
        return json_error(err), 400
    return apply_op('op_update_device_feature_object', id_, **request.json,
                    error_code=404)
