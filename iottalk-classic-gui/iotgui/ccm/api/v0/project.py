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
            'p_name': 'project name',
        }

    Response HTTP 201::

        {
            'state': 'ok',
            'p_id': 42,
        }

    Response if project name duplicated::

        {
            'state': 'error',
            'reason': 'project name already exists',
        }
    '''
    err = invalid_input(request.json, {'p_name': str})
    if err:
        return json_error(err), 400

    p_name = request.json['p_name']
    return apply_op('op_create_project', p_name, status_code=201)


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def list_():
    '''
    Response::

        {
            'state': 'ok',
            'data': [
                {
                    'exception': '',
                    'p_id': 1,
                    'p_name': 'test',
                    'restart': false,
                    'sim': 'off',
                    'status': 'on',
                    'u_id': 1
                },
            ],
        }
    '''
    return apply_op('op_get_project_list', post_proc=wrap_data)


@api.route('/<int:pid>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def delete(pid):
    '''
    Response::

        {
            'state': 'ok',
            'p_id': 42,
        }

    Response if project not found::

        {
            'state': 'error',
            'reason': 'project 42 not found',
        }
    '''
    return apply_op('op_delete_project', pid, error_code=404)


@api.route('/<int:pid>', methods=['GET'], strict_slashes=False)
@api_login_required
def project_get(pid):
    '''
    Response::

        {
            'state': 'ok',
            'data': {
                // project info
            },
        }

    Response if not project not found, HTTP 404 is returned::

        {
            'state': 'error',
            'reason': 'project not found',
        }
    '''
    return apply_op('op_get_project_info', pid, post_proc=wrap_data,
                    error_code=404)


@api.route('/<string:p_name>', methods=['GET'], strict_slashes=False)
@api_login_required
def project_get_by_name(p_name):
    '''
    Response::

        {
            'state': 'ok',
            'data': {
                // project info
            },
        }

    Response if not project not found, HTTP 404 is returned::

        {
            'state': 'error',
            'reason': 'project not found',
        }
    '''
    return apply_op('op_get_project_info',
                    run_op('op_search_project', p_name),
                    post_proc=wrap_data,
                    error_code=404)


@api.route('/<int:pid>', methods=['POST'], strict_slashes=False)
@api_login_required
def project_update(pid):
    '''
    Request::

        {
            'status': 'on' | 'off',
        }

    Response::

        {
            'state': ok,
            'p_id': 42,
            'status': 'on',
        }
    '''
    s = request.json.get('status')
    if s not in ('on', 'off'):
        return json_error('invalid status'), 400

    return apply_op('op_update_project', pid, s, error_code=404)
