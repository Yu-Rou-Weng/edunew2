import logging

from flask import request

from iotgui import config
from iotgui.ccm.api.utils import blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op, wrap_data

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/<int:pid>', methods=['GET'], strict_slashes=False)
@api_login_required
def simulation_get(pid):
    '''
    Response::

        {
            'state': 'ok',
            'data': 'on' / 'off'
        }

    Response if not project not found, HTTP 404 is returned::

        {
            'state': 'error',
            'reason': 'project not found',
        }
    '''
    return apply_op('op_get_simulation_status', pid, post_proc=wrap_data,
                    error_code=404)


@api.route('/<int:pid>', methods=['POST'], strict_slashes=False)
@api_login_required
def simulation_update(pid):
    '''
    Request::

        {
            'sim': 'on' | 'off',
        }

    Response::

        {
            'state': ok,
            'p_id': 42,
            'sim': 'on',
        }
    '''
    s = request.json.get('sim')
    if s not in ('on', 'off'):
        return json_error('invalid sim'), 400

    return apply_op('op_update_simulation', pid, s, error_code=404)
