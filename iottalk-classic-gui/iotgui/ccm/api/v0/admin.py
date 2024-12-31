import logging

from flask import jsonify, request

from iotgui import config, db
from iotgui.ccm import account
from iotgui.ccm.api.const import APIResponse
from iotgui.ccm.api.utils import api_admin_required
from iotgui.ccm.api.utils import blueprint, invalid_input, json_error
from iotgui.ccm.modules.utils import CCMError, Context, record_parser
from iotgui.ccm.mqttclient import mqtt_module

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.admin\033[0m".format(config.LOG_COLOR_GUI))


@api_admin_required
def run_admin_op(op: str, u_id: int, wrap: callable = None, *args, **kwargs):
    ret = APIResponse.OK
    try:
        method = getattr(mqtt_module, op)
        with db.session_scope() as db_session:
            ctx = Context(u_id, db_session)
            result = method(ctx, *args, **kwargs)
            if wrap:
                result = wrap(result)
            ret.update(result)
    except CCMError as e:
        return json_error(e.msg), 404

    return jsonify(ret)


@api.route('/user', methods=['GET'], strict_slashes=False)
@api_admin_required
def user_get():
    '''
    Response::

        {
            'state': 'ok',
            'data': [
                {
                    'u_id': 1,
                    'u_name': 'admin',
                    'is_admin': true
                },
                ...
            ]
        }
    '''

    ret = APIResponse.OK
    ret['data'] = []

    with db.session_scope() as db_session:
        users = db_session.query(db.model.User)
        for user in users:
            ret['data'].append(user.to_dict(('u_id', 'u_name', 'is_admin')))

    return jsonify(ret)


@api.route('/user/pass', methods=['POST'], strict_slashes=False)
@api_admin_required
def user_pass():
    '''
    :Allowed methods: `POST`

    Request::

        {
            "id": 2,
            "password": "newpass",
        }

    Response::

        {
            "state": "ok" | "error",
            "id": 2,  // user id
            "reason": "...",  // if error
        }
    '''
    err = invalid_input(request.json, {'id': int, 'password': str})
    if err:
        return json_error(err), 400

    ret = APIResponse.OK
    u_id = request.json['id']
    password = request.json['password']

    with db.session_scope() as session:
        if account.change_password(session, u_id, password):
            ret['id'] = u_id
            return jsonify(ret)

    return json_error('update fail'), 400


@api.route('/user/switch', methods=['POST'], strict_slashes=False)
@api_admin_required
def user_admin():
    '''
    :Allowed methods: `POST`

    Request::

        {
            "id": 2,
        }

    Response::

        {
            "state": "ok" | "error",
            "id": 2,  // user id
            "reason": "...",  // if error
        }
    '''
    err = invalid_input(request.json, {'id': int, 'is_admin': bool})
    if err:
        return json_error(err), 400

    ret = APIResponse.OK
    u_id = request.json['id']
    is_admin = request.json['is_admin']

    with db.session_scope() as session:
        if account.set_admin(session, u_id, is_admin):
            ret['id'] = u_id
            return jsonify(ret)

    return json_error('update fail'), 400


@api.route('/user', methods=['DELETE'], strict_slashes=False)
@api_admin_required
def user_delete():
    '''
    :Allowed methods: `DELETE`

    Request::

        {
            "id": 2,
        }

    Response::

        {
            "state": "ok" | "error",
            "id": 2,  // user id
            "reason": "...",  // if error
        }
    '''
    err = invalid_input(request.json, {'id': int})
    if err:
        return json_error(err), 400

    ret = APIResponse.OK
    u_id = request.json['id']

    with db.session_scope() as db_session:
        user = db_session.query(db.model.User).get(u_id)
        for p in user.projects:
            run_admin_op('op_delete_project', u_id, p_id=p.p_id)

        db_session.delete(user)
        db_session.commit()
        ret['id'] = u_id

    return jsonify(ret)


@api.route('/project', methods=['GET'], strict_slashes=False)
@api_admin_required
def project_get():
    '''
    Response::

        {
            'state': 'ok',
            'data': [
                {
                    'p_id': 1,
                    'p_name': 'my_project',
                    'status': 'on',
                    'sim': 'off',
                    'u_id': 1,
                    'u_name': 'admin'
                },
                ...
            ]
        }
    '''
    ret = APIResponse.OK
    ret['data'] = []

    with db.session_scope() as db_session:
        projects = (db_session.query(db.model.Project.p_id,
                                     db.model.Project.p_name,
                                     db.model.Project.status,
                                     db.model.Project.sim,
                                     db.model.Project.u_id,
                                     db.model.User.u_name)
                              .select_from(db.model.Project)
                              .join(db.model.User))
        for project in projects:
            ret['data'].append(record_parser(project))

    return jsonify(ret)


@api.route('/project/stop', methods=['POST'], strict_slashes=False)
@api_admin_required
def project_stop():
    '''
    :Allowed methods: `POST`

    Request::

        {
            "p_id": 1,
            "u_id": 1,
        }

    Response::

        {
            "state": "ok" | "error",
            "p_id": 1,  // project id
            "reason": "...",  // if error
        }
    '''
    err = invalid_input(request.json, {'p_id': int, 'u_id': int})
    if err:
        return json_error(err), 400

    u_id = request.json['u_id']
    p_id = request.json['p_id']

    return run_admin_op('op_update_project', u_id, p_id=p_id, status='off')


@api.route('/project/delete', methods=['POST'], strict_slashes=False)
@api_admin_required
def project_delete():
    '''
    :Allowed methods: `POST`

    Request::

        {
            "p_id": 1,
            "u_id": 1,
        }

    Response::

        {
            "state": "ok" | "error",
            "p_id": 1,  // project id
            "reason": "...",  // if error
        }
    '''
    err = invalid_input(request.json, {'p_id': int, 'u_id': int})
    if err:
        return json_error(err), 400

    u_id = request.json['u_id']
    p_id = request.json['p_id']

    return run_admin_op('op_delete_project', u_id, p_id=p_id)


@api.route('/device', methods=['GET'], strict_slashes=False)
@api_admin_required
def device_get():
    '''
    Response::

        {
            'state': 'ok',
        }
    '''
    ret = APIResponse.OK
    ret['data'] = []

    with db.session_scope() as db_session:
        devices = db_session.query(db.model.Device)
        for device in devices:
            d = record_parser(device)

            ps = (db_session.query(db.model.Project.p_name,
                                   db.model.User.u_name)
                            .select_from(db.model.DeviceObject)
                            .join(db.model.Project)
                            .join(db.model.User)
                            .filter(db.model.DeviceObject.d_id == device.d_id)
                            .all())
            d['projects'] = ['{} ({})'.format(p.p_name, p.u_name) for p in ps]

            ret['data'].append(d)

    return jsonify(ret)


@api.route('/device/unbind', methods=['POST'], strict_slashes=False)
@api_admin_required
def device_unbind():
    '''
    :Allowed methods: `POST`

    Request::

        {
            "d_id": 1,
        }

    Response::

        {
            "state": "ok" | "error",
            "d_id": 1,  // device id
            "reason": "...",  // if error
        }
    '''
    err = invalid_input(request.json, {'d_id': int})
    if err:
        return json_error(err), 400

    d_id = request.json['d_id']

    with db.session_scope() as db_session:
        dos = (db_session.query(db.model.DeviceObject.do_id,
                                db.model.Project.u_id)
                         .select_from(db.model.DeviceObject)
                         .join(db.model.Project)
                         .filter(db.model.DeviceObject.d_id == d_id)
                         .all())

        for do in dos:
            run_admin_op('op_unbind_device', do.u_id, do_id=do.do_id)

    ret = APIResponse.OK
    ret['d_id'] = d_id
    return jsonify(ret)
