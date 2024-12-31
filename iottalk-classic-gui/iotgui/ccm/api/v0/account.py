import logging

import flask_login

from flask import jsonify, request
from flask import session as http_session

from iotgui import config, db
from iotgui.ccm import account
from iotgui.ccm.api import redis
from iotgui.ccm.api.const import APIResponse
from iotgui.ccm.api.utils import api_login_required, apply_op
from iotgui.ccm.api.utils import blueprint, invalid_input, json_error

api = blueprint(__name__, __file__)
log = logging.getLogger("{}ccm.api.v0.account\033[0m".format(config.LOG_COLOR_GUI))


@api.route('/login', methods=['POST'], strict_slashes=False)
def login():
    """
    :Allowed methods: `POST`

    Request::

        {
            "username": "foo",
            "password": "bar",
        }

    Response::

        {
            "state": "ok" | "error",
            "id": 42,  // user id
            "reason": "...",  // if error
        }
    """

    if flask_login.current_user.is_authenticated:
        ret = APIResponse.OK
        ret['id'] = http_session['user_id']
        return jsonify(ret)

    if config.OAUTH2_CLIENT_ID:
        return json_error("Only allow oauth2 access token login."), 400

    err = invalid_input(request.json, {'username': str, 'password': str})
    if err:
        return json_error(err), 400

    username = request.json['username']
    password = request.json['password']
    ret = APIResponse.OK

    with db.session_scope() as db_session:
        # check user from db
        user = account.auth(username, password, db_session)
        # login failed
        if not user:
            return json_error('invalid username or password'), 401
        # user login
        account.login_user(user, http_session, redis)
        ret['id'] = user.u_id

    return jsonify(ret)


@api.route('/oauth2', methods=['POST'], strict_slashes=False)
def oauth2_login():
    """
    :Allowed methods: `POST`

    Request::

        {
            "access_token": "foo_bar!",
        }

    Response::

        {
            "state": "ok" | "error",
            "id": 42,  // user id
            "reason": "...",  // if error
        }
    """

    if flask_login.current_user.is_authenticated:
        ret = APIResponse.OK
        ret['id'] = http_session['user_id']
        return jsonify(ret)

    if not config.OAUTH2_CLIENT_ID:
        return json_error("Only allow username/password login."), 400

    err = invalid_input(request.json, {'access_token': str})
    if err:
        return json_error(err), 400

    access_token = request.json['access_token']
    response = account.oauth2.introspect_access_token(access_token)

    if not response:
        return json_error('Invalid access_token.'), 400

    ret = APIResponse.OK
    with db.session_scope() as db_session:
        # check user from db
        user = account.oauth2.auth(response.get('sub'), db_session)
        # login failed
        if not user:
            user = db.model.User(
                sub=response.get('sub'),
                u_name=response.get('preferred_username'),
                passwd='',
                email=response.get('email')
            )
            db_session.add(user)
            db_session.commit()
        # user login
        account.login_user(user, http_session, redis)
        ret['id'] = user.u_id

    return jsonify(ret)


@api.route('/logout', strict_slashes=False)
@api_login_required
def logout():
    account.logout_user(http_session, redis)
    return jsonify(APIResponse.OK)


@api.route('/create', methods=['POST'], strict_slashes=False)
def create():
    '''
    Response::

        {
            'state': 'ok',
            'id': 42,
        }
    '''
    if config.OAUTH2_CLIENT_ID:
        return json_error("This IoTtalk use Account Subsystem, \
            and does not allow to create native account."), 400

    err = invalid_input(request.json, {'username': str, 'password': str})
    if err:
        return json_error(err), 400

    ret = APIResponse.OK
    username = request.json['username']
    password = request.json['password']

    with db.session_scope() as session:
        if account.is_exist(session, username):
            return json_error('username already exists'), 400

        user = account.create(session, username, password)
        ret['id'] = user.u_id

    return jsonify(ret)


@api.route('/', methods=['DELETE'], strict_slashes=False)
@api_login_required
def delete():
    '''
    Response::

        {
            'state': 'ok',
        }
    '''
    with db.session_scope() as db_session:
        user = db_session.query(db.model.User).get(http_session['user_id'])
        for p in user.projects:
            apply_op('op_delete_project', p.p_id)

    # seems that it need different db_session for deleting user account record
    with db.session_scope() as db_session:
        account.delete(db_session, http_session, redis)
    return jsonify(APIResponse.OK)


@api.route('/', methods=['GET'], strict_slashes=False)
@api_login_required
def profile():
    '''
    Get the user profile

    Response::
        {
            'state': 'ok',
            'u_id': 42,
            'u_name': 'Foo',
            'is_admin': false,
        }
    '''

    with db.session_scope() as db_session:
        user = db_session.query(db.model.User).get(http_session['user_id'])

        return jsonify({
            'u_id': user.u_id,
            'u_name': user.u_name,
            'is_admin': user.is_admin,
            **APIResponse.OK
        })
