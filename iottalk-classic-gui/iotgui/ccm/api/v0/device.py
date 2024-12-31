import logging

from iotgui import config
from iotgui.ccm.api.utils import blueprint, api_login_required
from iotgui.ccm.api.utils import json_error, apply_op
from iotgui.ccm.modules.utils import Context
from iotgui.ccm.mqttclient import mqtt_module
from iotgui.db import session_scope

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.api\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def list_(pid, do_id):
    '''
    Response::

        {
            'state': 'ok',
            'do_id': 42,
            'device_list': [
                {
                    'd_id': 24,
                    'd_name': 'FooDevice',
                    'dm_id': 5,
                    'is_sim': false,
                    'mac_addr': '...',
                    'register_time': '...',
                    'status': 'online',
                    'u_id': 123,
                },
                ...
            ],
        }
    '''
    def f(x):
        return {
            'data': x['device_list'],
            'do_id': x['do_id'],
        }

    return apply_op('op_get_device_list', do_id, post_proc=f, error_code=404)


@api.route('/bind/<int:d_id>/', methods=['POST'], strict_slashes=False)
@api_login_required
def bind(pid, do_id, d_id):
    '''
    Response::

        {
            'state': 'ok',
            'd_name': 'FooDevice',
        }
    '''
    # TODO: handle param ``check_sim`` ?
    return apply_op('op_bind_device', do_id, d_id, error_code=404)


@api.route('/bind/<string:mac_addr>/', methods=['POST'], strict_slashes=False)
@api_login_required
def bind_mac(pid, do_id, mac_addr):
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        dev = mqtt_module._get_device_by_mac_addr(ctx, mac_addr)
        if dev is None:
            return json_error('unknown mac_addr'), 404
        return apply_op('op_bind_device', do_id, dev.d_id, error_code=404)


@api.route('/unbind/', methods=['POST'], strict_slashes=False)
@api_login_required
def unbind(pid, do_id):
    '''
    Response::

        {
            'state': 'ok',
            'do_id': 42,
        }
    '''
    # TODO: handle param ``check_sim`` ?
    return apply_op('op_unbind_device', do_id, error_code=404)
