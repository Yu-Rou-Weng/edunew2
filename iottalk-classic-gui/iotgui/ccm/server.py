#!/usr/bin/env python3
import datetime
import json
import logging
import os
import uuid

import flask_login
import pytz

from authlib.integrations.flask_client import OAuth
from flask import (
    Flask, abort, make_response, redirect, render_template, url_for,
    request, send_from_directory, session as http_session, jsonify)
from flask_session import Session as flask_session, RedisSessionInterface
from redis import StrictRedis
from sqlalchemy import or_
from werkzeug.middleware.proxy_fix import ProxyFix


from iotaa.client import Client as AAClient
from iotaa.client.exceptions import AAReadTimeout
from iotgui import config, db
from iotgui.ccm import account
from iotgui.ccm.api.v0.alias import api as alias_api_v0
from iotgui.ccm.api.v0.account import api as account_api_v0
from iotgui.ccm.api.v0.admin import api as admin_api_v0
from iotgui.ccm.api.v0.devicefeature import api as devicefeature_api_v0
from iotgui.ccm.api.v0.devicefeatureobject import api as devicefeatureobject_api_v0
from iotgui.ccm.api.v0.device import api as device_api_v0
from iotgui.ccm.api.v0.devicemodel import api as devicemodel_api_v0
from iotgui.ccm.api.v0.project import api as project_api_v0
from iotgui.ccm.api.v0.deviceobject import api as deviceobject_api_v0
from iotgui.ccm.api.v0.networkapplication import api as na_api_v0
from iotgui.ccm.api.v0.function import api as function_api_v0
from iotgui.ccm.api.v0.simulation import api as sim_api_v0
from iotgui.ccm.api.utils import api_admin_required, json_error
from iotgui.ccm.modules.utils import record_parser
from iotgui.db import model
from iotutils.aa.const import MosquittoPermission, ResponseCode

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# use OAuth2 for account
if config.OAUTH2_CLIENT_ID:
    oauth2_client = OAuth()
    oauth2_client.init_app(app)

    # Register OAuth2 Provider information
    #
    # Ref: https://tinyurl.com/j6cnk22s
    oauth2_client.register(
        name='iottalk',
        client_id=config.OAUTH2_CLIENT_ID,
        client_secret=config.OAUTH2_CLIENT_SECRET,
        server_metadata_url=config.OIDC_DISCOVERY_ENDPOINT,
        client_kwargs={'scope': 'openid', }
    )

# API blueprint
app.register_blueprint(account_api_v0, url_prefix='/api/v0/account')
app.register_blueprint(project_api_v0, url_prefix='/api/v0/project')
app.register_blueprint(deviceobject_api_v0,
                       url_prefix='/api/v0/project/<int:pid>/deviceobject')
app.register_blueprint(
    device_api_v0,
    url_prefix='/api/v0/project/<int:pid>/deviceobject/<int:do_id>/device')
app.register_blueprint(na_api_v0, url_prefix='/api/v0/project/<int:pid>/na')
app.register_blueprint(devicemodel_api_v0, url_prefix='/api/v0/devicemodel')
app.register_blueprint(devicefeature_api_v0, url_prefix='/api/v0/devicefeature')
app.register_blueprint(
    devicefeatureobject_api_v0,
    url_prefix='/api/v0/project/<int:pid>/deviceobject/<int:do_id>/devicefeatureobject')
app.register_blueprint(sim_api_v0, url_prefix='/api/v0/simulation')
app.register_blueprint(alias_api_v0, url_prefix='/api/v0/alias')
app.register_blueprint(function_api_v0, url_prefix='/api/v0/function')
app.register_blueprint(admin_api_v0, url_prefix='/api/v0/admin')

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# store session user data for mqtt
# in redis hashmap ('user', session['session_id'], <u_id>)
redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)

# Flask server side session
RedisSessionInterface.serializer = json
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis
flask_session(app)

log = logging.getLogger("{}Flask\033[0m".format(config.LOG_COLOR_GUI))


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api'):
        return json_error('API not found'), 404
    return 'Not Found', 404


@login_manager.unauthorized_handler
def unauthorized_callback():
    next_uri = request.args.get('next', '/iottalk/ccm/' + request.endpoint)

    # unauthorized, redirect to login page
    if config.OAUTH2_CLIENT_ID:
        redirect_uri = url_for('auth_callback', _external=True)
        return oauth2_client.iottalk.authorize_redirect(redirect_uri, state=next_uri)

    return redirect(url_for('login', next=next_uri))


@login_manager.user_loader
def load_user(u_id):
    session = db.get_session()
    user = (session.query(model.User)
                   .filter(model.User.u_id == u_id)
                   .first())
    session.close()
    return user


@app.route('/register', methods=['GET', 'POST'])
def register():
    if config.OAUTH2_CLIENT_ID:
        return 'IoTtalk uses Oauth2 as the account system'\
               'and no longer provides the registration function', 404

    if 'POST' == request.method:
        # check post data
        if not request.form.get('username') or not request.form.get('password'):
            return render_template('login.html',
                                   error_msg='Wrong username or pass.')

        username = request.form.get('username').strip()
        password = request.form.get('password')

        # check user's data
        if not username or not password:
            return render_template('login.html',
                                   error_msg='Wrong username or pass.')

        # get username exist in db
        with db.session_scope() as session:
            if account.is_exist(session, username):
                return render_template('login.html',
                                       error_msg='Username exist.')

            account.create(session, username, password)

        return redirect(url_for('login',
                                next=request.args.get('next', '/iottalk/ccm/connection')))

    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # check user logged. if user logged, redirect to ``next``
    if flask_login.current_user.is_authenticated:
        return redirect(request.args.get('next', '/iottalk/ccm/connection'))

    if config.OAUTH2_CLIENT_ID:
        return unauthorized_callback()

    if 'POST' == request.method:
        # check post data
        if not request.form.get('username') or not request.form.get('password'):
            return render_template('login.html',
                                   is_login=True,
                                   error_msg='Wrong username or pass.')

        username = request.form.get('username').strip()
        password = request.form.get('password')

        with db.session_scope() as db_session:
            # check user from db
            user = account.auth(username, password, db_session)

            # login failed
            if not user:
                return render_template('login.html',
                                       is_login=True,
                                       error_msg='Wrong username or pass.')

            # user login
            account.login_user(user, http_session, redis)

        return redirect(request.args.get('next', '/iottalk/ccm/connection'))

    return render_template('login.html', is_login=True)


@app.route('/auth/callback', methods=['GET'])
def auth_callback():
    if not config.OAUTH2_CLIENT_ID:
        return "Oauth2 doesn't support, please contact the administrator."
    # Check whether the query parameters has one named `code`
    if not request.args.get('code'):
        if flask_login.current_user.is_authenticated:
            # Redirect user-agent to the index page if a user is already authenticated
            return redirect(url_for('index'))

        redirect_uri = url_for('auth_callback', _external=True)
        next_uri = request.args.get('next', '/' + request.endpoint)
        # Redirect user-agent to the authorization endpoint if a user is not authenticated
        return oauth2_client.iottalk.authorize_redirect(redirect_uri, state=next_uri)

    try:
        # Exchange access token with an authorization code with token endpoint
        #
        # Ref: https://docs.authlib.org/en/stable/client/frameworks.html#id1
        token_response = oauth2_client.iottalk.authorize_access_token()

        # Parse the received ID token
        user_info = oauth2_client.iottalk.parse_id_token(token_response)
    except Exception:
        log.exception('Get access token failed:')
        return 'Something is broken...'

    try:
        db_session = db.get_session()
        user_record = (db_session.query(model.User)
                                 .filter_by(sub=user_info.get('sub'))
                                 .first())

        if not user_record:
            # Create a new user record if there does not exist an old one
            user_record = model.User(
                sub=user_info.get('sub'),
                u_name=user_info.get('preferred_username'),
                passwd='',
                email=user_info.get('email')
            )
            db_session.add(user_record)

        # Query the refresh token record
        refresh_token_record = \
            db_session.query(model.RefreshToken).filter_by(u_id=user_record.u_id).first()

        if not refresh_token_record:
            # Create a new refresh token record if there does not exist an old one
            refresh_token_record = model.RefreshToken(
                token=token_response.get('refresh_token'),
                user=user_record
            )
            db_session.add(refresh_token_record)
        elif token_response.get('refresh_token'):
            # If there is a refresh token in a token response, it indicates that
            # the old refresh token is expired, so we need to update the old refresh
            # token with a new one.
            refresh_token_record.token = token_response.get('refresh_token')

        # Create a new access token record
        access_token_record = model.AccessToken(
            token=token_response.get('access_token'),
            expires_at=(
                datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
                + datetime.timedelta(seconds=token_response.get('expires_in', 0))
            ),
            user=user_record,
            refresh_token=refresh_token_record
        )
        db_session.add(access_token_record)

        # Flush all the pending operations to the database so we can get the actual
        # id value.
        db_session.flush()

        # Store the access token ID to HTTP session
        http_session['access_token_id'] = access_token_record.id

        # Login user
        account.login_user(user_record, http_session, redis)
    except Exception as e:
        log.error('Save User error....')
        db_session.rollback()
        raise e
    else:
        db_session.commit()
        account.login_user(user_record, http_session, redis)
    finally:
        db_session.close()

    return redirect(request.args.get('state', url_for('index')))


@app.route('/logout')
@flask_login.login_required
def logout():
    if not flask_login.current_user.is_authenticated:
        return redirect(url_for('index'))

    account.logout_user(http_session, redis)
    # return to index page
    return redirect(url_for('index'))


@app.route('/connection', methods=['GET'])
@flask_login.login_required
def connection():
    # update user data cache
    if http_session.get('session_id') and redis.hget('user', http_session['session_id']):
        redis.hset('user', http_session['session_id'], http_session['user_id'])
    else:
        return unauthorized_callback()

    session = db.get_session()
    query_projects = (session.query(model.Project)
                             .filter(model.Project.u_id == http_session['user_id'])
                             .all())
    projects = []
    for project in query_projects:
        projects.append(record_parser(project))

    query_dm = (session.query(model.DeviceModel)
                       .join(model.DM_DF)
                       .join(model.DF_Parameter)
                       .filter(or_(model.DF_Parameter.u_id == http_session['user_id'],
                                   model.DF_Parameter.u_id.is_(None)))
                       .group_by(model.DeviceModel.dm_id)
                       .order_by(model.DeviceModel.dm_name)
                       .all())
    dm_list = []
    for dm in query_dm:
        dm_list.append(record_parser(dm))

    user = (session.query(model.User)
                   .filter(model.User.u_id == http_session['user_id'])
                   .first())
    username = user.u_name if user else ''
    u_id = user.u_id if user else ''

    session.close()

    subsystem_dms = [
        {
            'sysname': 'datatalk',
            'header': 'DataBank',
            'endpoints': config.DATATALK_ENDPOINTS,
        },
        {
            'sysname': 'aitalk',
            'header': 'ML (AI)',
            'endpoints': config.AITALK_ENDPOINTS,
        },
    ]

    # render index with login user data
    return render_template('connection.html',
                           _id=http_session['session_id'],
                           projects=projects,
                           username=username,
                           u_id=u_id,
                           dm_list=dm_list,
                           simtalk=config.SIMTALK_ENDPOINT,
                           sa_gen=config.SAGEN_ENDPOINT,
                           subsystem_dms=subsystem_dms)


@app.route('/management', methods=['GET'])
@flask_login.login_required
def management():
    return render_template('manage.html',
                           _id=http_session['session_id'],)


@app.route('/device', methods=['GET'])
@flask_login.login_required
def device():
    time_filter = ()
    if config.OWNERSHIP_TIMEOUT:
        time_filter = \
            datetime.datetime.now() - datetime.timedelta(0, config.OWNERSHIP_TIMEOUT)
        time_filter = (model.Device.register_time > time_filter,)

    session = db.get_session()
    devices = (session.query(model.Device)
                      .filter(model.Device.u_id.is_(None),
                              *time_filter))
    devices = [record_parser(device) for device in devices]
    session.close()
    return render_template('device_ownership.html',
                           _id=http_session['session_id'],
                           devices=devices)


@app.route('/device_confirm', methods=['POST'])
@flask_login.login_required
def device_confirm():
    d_id = request.form.get('d_id')

    # check data
    if not d_id:
        abort(404)

    session = db.get_session()
    (session.query(model.Device)
            .filter(model.Device.d_id == d_id)
            .update({'u_id': http_session['user_id']}))
    session.commit()
    session.close()

    return 'ok'


@app.route('/export_project', methods=['GET'])
@flask_login.login_required
def export_project():
    """
    input value
        {
            'p_id': 'p_id',
        }
    output value
        {
            project: {
                p_name : "",
                DeviceObject: {
                    `do_id`: {
                        dm_name: "",
                        do_idx: "",
                        dfo: {
                            `dfo_id`: {
                                df_name: "",
                                alias_name: "",
                            },
                            ...
                        }
                    },
                    ...
                },
                NetworkApplication: [
                    {
                        na_name: "",
                        na_idx: "",
                        DF_Module: [
                            dfo_id: "",
                            param_i: "",
                            idf_type: "",
                            fn_name: "",
                            min: "",
                            max: "",
                            normalization: "",
                        ],
                        MultipleJoin_module: [
                            {
                                param_i: "",
                                fn_name: "",
                                dfo_id: ``,
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        }
    """
    session = db.get_session()
    p_id = request.args.get('p_id')
    u_id = http_session['user_id']

    proj = session.query(model.Project).get(p_id)
    if proj is None or proj.user.u_id != u_id:  # ownership checking
        return abort(404)

    response = jsonify({'project': proj.export()})
    response.headers["Content-Disposition"] = ("attachment; "
                                               "filename={}.json".format(proj.p_name))
    session.close()
    return response


@app.route('/import_project', methods=['POST', 'GET'])
@flask_login.login_required
def import_project():
    """
    input value
        - ``p_name``: a new project name
        - ``importfilename``: file object
    """
    upload_file = request.files.get('importfilename', None)
    if not upload_file.filename:
        return 'No file selected', 400

    try:
        f = json.load(upload_file.stream)
    except json.JSONDecodeError:
        return 'Invalid format', 400

    project = f.get('project')
    if not project:
        return 'Invalid format', 400

    # project name checking
    p_name = request.form.get('p_name')
    if not p_name:
        return 'Please select a new project name', 400

    with db.session_scope() as sess:
        if sess.query(model.Project).filter_by(p_name=p_name).count():
            return 'Project name already exists', 400

    session = db.get_session()
    p_id = None
    try:
        # Project
        new_project = model.Project(
            p_name=p_name,
            status='off',
            restart=0,
            u_id=http_session['user_id'],
            exception='',
            sim='off',
        )
        session.add(new_project)
        session.commit()
        p_id = new_project.p_id
        dfo_mapping = {}  # map old dfo_id to new dfo_id

        if not p_id:
            return Exception("Project saving failed")

        # DeviceObject
        for do_id, do in project['DeviceObject'].items():
            query_dm = (session.query(model.DeviceModel.dm_id)
                               .select_from(model.DeviceModel)
                               .filter(model.DeviceModel.dm_name == do['dm_name'])
                               .first())
            if not query_dm:
                raise Exception(("DeviceModel: \"{}\" not find!\n"
                                 .format(do['dm_name'])))

            new_do = model.DeviceObject(
                dm_id=query_dm.dm_id,
                p_id=p_id,
                do_idx=do['do_idx'],
                d_id=None,
            )
            session.add(new_do)
            session.commit()
            do['do_id'] = new_do.do_id

            # DFObject
            for dfo_id, dfo in do['dfo'].items():
                query_df = (session.query(model.DeviceFeature.df_id)
                                   .select_from(model.DeviceFeature)
                                   .filter(model.DeviceFeature.df_name == dfo['df_name'])
                                   .first())

                if not query_df:
                    raise Exception(("DeviceFeatre: \"{}\" not find!\n"
                                     .format(dfo['df_name'])))

                new_dfo = model.DFObject(
                    do_id=do['do_id'],
                    df_id=query_df.df_id,
                    alias_name=dfo['alias_name']
                )
                session.add(new_dfo)
                session.commit()
                dfo['dfo_id'] = new_dfo.dfo_id
                dfo_mapping[dfo_id] = {'dfo_id': new_dfo.dfo_id,
                                       'df_id': query_df.df_id}

        # NetworkApplication
        for na in project['NetworkApplication']:
            new_na = model.NetworkApplication(
                na_name=na['na_name'],
                na_idx=na['na_idx'],
                p_id=p_id,
            )
            session.add(new_na)
            session.commit()
            na['na_id'] = new_na.na_id

            # DF_Module
            for dfm in na['DF_Module']:
                fn_id = None
                if dfm['fn_name']:
                    query_fn = (session.query(model.Function.fn_id)
                                       .select_from(model.Function)
                                       .filter(model.Function.fn_name == dfm['fn_name'])
                                       .first())

                    if not query_fn:
                        raise Exception(
                            "Function: \"{}\" not find!\n".format(dfm['fn_name']))
                    fn_id = query_fn.fn_id

                if str(dfm['dfo_id']) not in dfo_mapping.keys():
                    raise Exception("dfo mapping wrong")

                new_dfm = model.DF_Module(
                    na_id=new_na.na_id,
                    dfo_id=dfo_mapping[str(dfm['dfo_id'])]['dfo_id'],
                    param_i=dfm['param_i'],
                    idf_type=dfm['idf_type'],
                    fn_id=fn_id,
                    min=dfm['min'],
                    max=dfm['max'],
                    normalization=dfm['normalization'],
                    color='black',
                )
                session.add(new_dfm)
                session.commit()

                if fn_id:
                    query_fsdf = \
                        (session.query(model.FunctionSDF.fnsdf_id)
                                .filter(
                                    model.FunctionSDF.df_id == dfo_mapping[str(dfm['dfo_id'])]['df_id'],  # noqa: E501
                                    model.FunctionSDF.fn_id == fn_id,
                                    model.FunctionSDF.display == 1,
                                    model.FunctionSDF.u_id.is_(None))
                                .first())

                    if not query_fsdf:
                        new_fsdf = model.FunctionSDF(
                            df_id=dfo_mapping[str(dfm['dfo_id'])]['df_id'],
                            fn_id=fn_id,
                            display=1,
                        )
                        session.add(new_fsdf)
                        session.commit()

            # MultipleJoin_Module
            for mjm in na['MultipleJoin_Module']:
                fn_id = None
                if mjm['fn_name']:
                    query_fn = (session.query(model.Function.fn_id)
                                       .select_from(model.Function)
                                       .filter(model.Function.fn_name == mjm['fn_name'])
                                       .first())

                    if not query_fn:
                        raise Exception(("Function: \"{}\" not find!\n"
                                         .format(dfm['fn_name'])))
                    fn_id = query_fn.fn_id

                if str(mjm['dfo_id']) not in dfo_mapping.keys():
                    raise Exception("dfo mapping wrong")

                new_mjm = model.MultipleJoin_Module(
                    na_id=new_na.na_id,
                    param_i=mjm['param_i'],
                    fn_id=fn_id,
                    dfo_id=dfo_mapping[str(mjm['dfo_id'])]['dfo_id'],
                )
                session.add(new_mjm)
                session.commit()

                if fn_id:
                    query_fsdf = (session.query(model.FunctionSDF.fnsdf_id)
                                         .filter(model.FunctionSDF.df_id is None,
                                                 model.FunctionSDF.fn_id == fn_id,
                                                 model.FunctionSDF.display == 1,
                                                 model.FunctionSDF.u_id is None,)
                                         .first())

                    if not query_fsdf:
                        new_fsdf = model.FunctionSDF(
                            df_id=None,
                            fn_id=fn_id,
                            display=1,
                        )
                        session.add(new_fsdf)
                        session.commit()

    except Exception as e:
        if not p_id:
            return 'save error'

        query_na = (session.query(model.NetworkApplication)
                           .filter(model.NetworkApplication.p_id == p_id)
                           .all())

        for na in query_na:
            (session.query(model.MultipleJoin_Module)
                    .filter(model.MultipleJoin_Module.na_id == na.na_id)).delete()

            (session.query(model.DF_Module)
                    .filter(model.DF_Module.na_id == na.na_id)).delete()
        (session.query(model.NetworkApplication)
                .filter(model.NetworkApplication.p_id == p_id)).delete()

        query_do = (session.query(model.DeviceObject)
                           .filter(model.DeviceObject.p_id == p_id))

        for do in query_do:
            (session.query(model.DFObject)
                    .filter(model.DFObject.do_id == do.do_id)).delete()

        (session.query(model.DeviceObject)
                .filter(model.DeviceObject.p_id == p_id)).delete()

        (session.query(model.Project)
                .filter(model.Project.p_id == p_id)).delete()

        session.commit()
        for a in e.args:
            print(a)
        return 'save error:\n' + str(e.args[0])

    session.close()
    return redirect("/connection#p_id=" + str(p_id), code=302)


@app.route('/')
def index():
    dir_ = os.path.join(config.WEB_DA_DIR_PATH, 'vp/py')
    vp_da_list = []

    for f in os.listdir(dir_):
        if f.endswith('.py'):
            vp_da_list.append(f.replace('.py', ''))

    vp_da_list.sort()

    session = db.get_session()
    device_list = (session.query(model.Device)
                          .filter(model.Device.device_webpage != '')
                          .all())
    session.close()
    return render_template('index.html',
                           vp_da_list=vp_da_list,
                           device_list=device_list)


@app.route('/da/<path:path>')
def web_da(path):
    fullpath = os.path.join(config.WEB_DA_DIR_PATH, path)
    no_cache_headers = {
        'Cache-Control': ('no-store, no-cache, must-revalidate, '
                          'post-check=0, pre-check=0, max-age=0'),
        'Pragma': 'no-cache',
        'Expires': '-1',
    }

    if os.path.exists(fullpath) and os.path.isdir(fullpath):
        if not fullpath.endswith('/'):
            response = make_response(redirect(os.path.join('da', path) + '/'))
            for key, val in no_cache_headers.items():
                response.headers[key] = val
            return response

        if os.path.exists(os.path.join(fullpath, 'index.html')):
            response = send_from_directory(fullpath, 'index.html')
            for key, val in no_cache_headers.items():
                response.headers[key] = val
            return response
    return send_from_directory(config.WEB_DA_DIR_PATH, path)


@app.route('/api/v1/get_alias')
def get_alias():
    mac_addr = request.args.get('mac_addr')
    df_name = request.args.get('df_name')

    session = db.get_session()
    query = (session.query(model.DFObject.alias_name)
                    .select_from(model.Device)
                    .filter(model.Device.mac_addr == mac_addr)
                    .join(model.DeviceObject)
                    .join(model.DFObject)
                    .join(model.DeviceFeature)
                    .filter(model.DeviceFeature.df_name == df_name)
                    .first())
    if query:
        alias_name = query[0]
    else:
        alias_name = df_name

    session.close()
    return alias_name


@app.route('/mqtt_url')
def mqtt_url():
    aa_client = AAClient(config.AA_HOST, config.AA_PORT, 'ccm', config.AA_TOKEN)
    mqtt_id = str(uuid.uuid4())

    api_response = {
        'id': mqtt_id,
        'host': config.MQTT.host,
        'port': config.MQTT.port,
        'ws_scheme': config.MQTT.websocket_scheme,
        'ws_port': config.MQTT.websocket_port,
    }
    api_response_code = 200

    if config.ENABLE_MQTT_AUTH:
        try:
            aa_response = aa_client.add_a_new_credential([
                ('iottalk/api/gui/res/{}'.format(mqtt_id),
                 MosquittoPermission.SUBSCRIBE_READ, ),
                ('iottalk/api/gui/req/{}'.format(mqtt_id),
                 MosquittoPermission.WRITE, ),
            ])
        except AAReadTimeout:
            api_response = {}
            api_response_code = 504  # Gateway Timeout
        else:
            if aa_response.code == ResponseCode.OK:
                api_response['credential_id'] = aa_response.payload.get('credential_id')
                api_response['username'] = aa_response.payload.get('username')
                api_response['password'] = aa_response.payload.get('password')
            else:
                # The AA subsystem does not return a right response
                api_response = {}
                api_response_code = 500

    return jsonify(api_response), api_response_code


@app.route('/ec_endpoint')
def ec_endpoint():
    return jsonify({'ec_endpoint': config.EC_ENDPOINT})


@app.route('/simtalk_endpoint')
def simtalk_endpoint():
    return jsonify({'simtalk_endpoint': config.SIMTALK_ENDPOINT})


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/images/', 'favicon.ico')


@app.route('/admin')
@api_admin_required
def admin_page():
    return render_template('admin.html', user=http_session['user_id'])


# ################### http wrapper ####################
@app.before_request
def before_request():
    # set http session permanent
    http_session.permanent = True


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers['Cache-Control'] = ('no-store, no-cache, must-revalidate, '
                                  'post-check=0, pre-check=0, max-age=0')
    r.headers['Pragma'] = 'no-cache'
    r.headers['Expires'] = '-1'
    return r


def main():  # start CCM http server
    app.run(
        host=config.CCM_HOST,
        port=config.CCM_PORT,
        threaded=True,
        debug=config.IS_DEBUG,
    )
