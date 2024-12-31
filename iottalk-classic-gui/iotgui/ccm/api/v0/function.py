'''
Not Support: op_get_dfo_function_info
'''

import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/', methods=['PUT'], strict_slashes=False)
@api_login_required
def create():
    '''
    Create new Function.

    If function name is exist, update the function code for login user.
    Note: Function name should start with alphabet.

    Request::

        {
            'fn_name': 'sleep',
            'code': 'import time; time.sleep(1)',
            'df_id': 24 // optional, if give,
                        // this function code is for the Device Feature,
                        // o.w. for the join
        }

    Response::

        {
            'state': 'ok',
            'fn_id': 666,
            'fnvt_idx': 1
        }
    '''
    err = invalid_input(
        request.json,
        {'fn_name': str, 'code': str},
        {'df_id': (int, type(None))})

    if err:
        return json_error(err), 400
    return apply_op('op_create_function', **request.json, status_code=201)


@api.route('/<int:id_>', methods=['POST'], strict_slashes=False)
@api_login_required
def update(id_):
    '''
    Update the Function code.

    If 'fnvt_idx' given, check owner is correct, then update code and date.
    Otherwise, create new function version.

    Request::

        {
            'code': 'import time; time.sleep(1)',
            'df_id': 24,  // optional, if give,
                          // this function code is for the Device Feature,
                          // o.w. for the join
            'fnvt_idx': 1 // optional, if given,
                          // update the function code by version,
                          // else create new version
        }

    Response::

        {
            'state': 'ok',
            'fn_id': 666,
            'fnvt_idx': 1
        }
    '''
    err = invalid_input(
        request.json,
        {'code': str},
        {'df_id': (int, type(None)), 'fnvt_idx': (int, type(None))})

    if err:
        return json_error(err), 400
    return apply_op('op_update_function', id_, **request.json, error_code=404)


@api.route('/<int:id_>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def delete(id_):
    '''
    Delete the Function by given fn_id.

    Server will check the Function is used or not.
    If delete successful, server will return fn_id, else return NULL

    Response::

        {
            'state': 'ok',
            'fn_id': 666
        }
    '''
    return apply_op('op_delete_function', id_, error_code=404)


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def list_():
    '''
    Get all Functions.

    List all function name in Function which user can use.

    Response::

        {
            'state': 'ok',
            'fn_list': [
                {
                    'fn_id': 666,
                    'fn_name': 'sleep'
                },
                ...
            ]
        }
    '''
    return apply_op('op_get_function_list', error_code=404)


@api.route('/devicefeature/<int:df_id>', methods=['GET'], strict_slashes=False)
@api_login_required
def list_df_functions(df_id):
    '''
    Get all Functions for Device Feature could use.

    The list of function only contain which store in FunctionSDF with
    login user and device feature.

    Response::

        {
            'state': 'ok',
            'fn_list': [
                {
                    'fn_id': 666,
                    'fn_name': 'sleep'
                },
                ...
            ]
        }
    '''
    return apply_op('op_get_device_feature_function_list', df_id, error_code=404)


@api.route('/networkapplication', methods=['GET'], strict_slashes=False)
@api_login_required
def list_na_functions():
    '''
    Get all Functions for Network Application could use.

    The list of function only contain which store in FunctionSDF with
    login user and NetworkApplication (df_id == None).

    Response::

        {
            'state': 'ok',
            'fn_list': [
                {
                    'fn_id': 666,
                    'fn_name': 'sleep'
                },
                ...
            ]
        }
    '''
    return apply_op('op_get_na_function_list')


@api.route('/<int:id_>/a', methods=['GET'], strict_slashes=False)
@api_login_required
def get_all_versions(id_):
    '''
    Get the Function's version list by given fn_id.

    Return general function version and user's function version.

    Response::

        {
            'state': 'ok',
            'fnvt_list': [
                {
                    'fnvt_id': 21,
                    'fn_id': 666,
                    'u_id': 1,
                    'date': '2020/01/01',
                    'code': 'import time; time.sleep(1)',
                    'completeness': 1,  // legacy
                    'is_switch': 0,     // legacy
                    'non_df_args': ''   // legacy
                },
                ...
            ]
        }
    '''
    return apply_op('op_get_function_version_list', id_, error_code=404)


@api.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@api_login_required
def get(id_):
    '''
    Get the latest Function's infomation by given fn_id.

    Response::

        {
            'state': 'ok',
            'data': {
                'fnvt_id': 21,
                'fn_id': 666,
                'date': '2020/01/01',
                'code': 'import time; time.sleep(1)',
            }
        }
    '''
    return apply_op(
        'op_get_function_info',
        fn_id=id_,
        post_proc=wrap_data,
        error_code=404
    )


@api.route('/version/<int:fnvt_idx>', methods=['GET'], strict_slashes=False)
@api_login_required
def get_version(fnvt_idx):
    '''
    Get the Function's infomation by given fnvt_idx.

    Response::

        {
            'state': 'ok',
            'data': {
                'fnvt_idx': 21,
                'fn_id': 666,
                'date': '2020/01/01',
                'code': 'import time; time.sleep(1)',
            }
        }
    '''
    return apply_op(
        'op_get_function_info',
        fnvt_idx=fnvt_idx,
        post_proc=wrap_data,
        error_code=404
    )


@api.route('/<int:fn_id>/SDF/', methods=['PUT'], strict_slashes=False)
@api.route('/<int:fn_id>/SDF/<int:df_id>', methods=['PUT'], strict_slashes=False)
@api_login_required
def create_sdf(fn_id, df_id=None):
    '''
    Add the Function to the usage list for
    Device Feature or Network Application.

    This addition will store in the FunctionSDF,
    and specified the login user.
    This API NOT support add the function to the usage list for general.

    Response::

        {
            'state': 'ok',
            'data': {
                'df_id': 21,
                'fn_id': 666
            }
        }
    '''
    return apply_op(
        'op_create_functionSDF',
        fn_id=fn_id,
        df_id=df_id,
        post_proc=wrap_data,
        status_code=201
    )


@api.route('/<int:fn_id>/SDF/', methods=['DELETE'], strict_slashes=False)
@api.route('/<int:fn_id>/SDF/<int:df_id>', methods=['DELETE'], strict_slashes=False)
@api_login_required
def delete_sdf(fn_id, df_id=None):
    '''
    Remove the Function to the usage list for Device Feature or Network Application.

    This will remove the specified setting which store in the FunctionSDF,
    and specified the login user.
    This API NOT support remove the function to the usage list for general.

    Response::

        {
            'state': 'ok',
            'data': {
                'df_id': 21,
                'fn_id': 666
            }
        }
    '''
    return apply_op(
        'op_delete_functionSDF',
        fn_id=fn_id,
        df_id=df_id,
        post_proc=wrap_data,
        error_code=404
    )
