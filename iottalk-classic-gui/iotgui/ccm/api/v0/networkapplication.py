import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/', methods=['PUT'], strict_slashes=False)
@api_login_required
def create(pid):
    '''
    Request::

        {
            'na_name': 'JoinFoo',
            'na_idx': 0,  // for GUI displaying, starting from 0
            'dfo_ids': [
                ... // can be found in project info
            ]
        }

    Response::

        {
            'state': 'ok',
            'na_id': 42,
        }
    '''
    err = invalid_input(request.json,
                        {'na_name': str, 'na_idx': int, 'dfo_ids': list})
    if err:
        return json_error(err), 400

    return apply_op('op_create_na', pid, **request.json)


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def list_(pid):
    '''
    Response::

        {
            'state': 'ok',
            'p_id': 42,
            'data': [
                ...
            ]
        }
    '''
    def f(x):
        x.update({'data': x.pop('na')})
        return x

    return apply_op('op_get_na_list', pid, post_proc=f, error_code=404)


@api.route('/<int:na_id>', methods=['GET'], strict_slashes=False)
@api_login_required
def info(pid, na_id):
    '''
    Response::

        {
            'state': 'ok',
            'data':{
                'na_id': 42,
                'na_name': 'FooJoin',
                'na_idx': '0',
                'input': [ <dfm_info>, ...],
                'output': [ <dfm_info>, ...],
                'multiple': [ <multiplejion_info>, ...]
                'fn_list': [ <fn_info>, ...]  //  for multiplejoin function
            }
        }
    '''
    return apply_op('op_get_na_info', na_id, pid, post_proc=wrap_data,
                    error_code=404)


@api.route('/<int:na_id>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def delete(pid, na_id):
    '''
    Response::

        {
            'state': 'ok',
            'na_id': 42,
        }
    '''
    return apply_op('op_delete_na', na_id, error_code=404)


@api.route('/<int:na_id>', methods=['POST'], strict_slashes=False)
@api_login_required
def update(pid, na_id):
    '''
    Request::

        {
            'na_name': 'new name',  // optional
            'multiplejoin_fn_id': 42,  // optional, the join function id,
                                       // `null` implies disabling the function.
            'dfm_list': [  // optional, a list of `dm_info`
                {
                    'dfo_id': 123,
                    'dfmp_list': [
                        ...,  // an instance of this list can be obtained
                              // from the return of the API
                              // `GET ../na/<na_id>/`.
                              // There are fields named `output[n].dfmp` and
                              // `input[n].dfmp`
                    ]
                },
                ...
            ],
        }

    Response::

        {
        }
    '''
    err = invalid_input(request.json, {}, {
        'na_name': (str, type(None)), 'multiplejoin_fn_id': (int, type(None)),
        'dfm_list': list})
    if err:
        return json_error(err), 400

    for x in request.json.get('dfm_list', []):
        err = invalid_input(x, {'dfo_id': int, 'dfmp_list': list}, {})
        if err:
            return json_error(err), 400

    return apply_op('op_update_na', na_id, **request.json)
