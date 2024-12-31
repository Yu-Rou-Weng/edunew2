import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import invalid_input, blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/<string:mac_addr>/<string:df_name>', methods=['GET'], strict_slashes=False)
@api_login_required
def get(mac_addr, df_name):
    '''
    Response::

        {
            'state': 'ok',
            'alias_name': 'Finn'
        }
    '''
    return apply_op('op_get_alias_name', mac_addr, df_name, error_code=404)


@api.route('/<string:mac_addr>/<string:df_name>', methods=['POST'], strict_slashes=False)
@api_login_required
def set(mac_addr, df_name):
    '''
    Request::

        {
            'alias_name': 'Finn'
        }

    Response::

        {
            'state': 'ok',
            'alias_name': 'Finn'
        }
    '''
    err = invalid_input(request.json, {'alias_name': str})
    if err:
        return json_error(err), 400
    return apply_op('op_set_alias_name', mac_addr, df_name, **request.json, error_code=404)
