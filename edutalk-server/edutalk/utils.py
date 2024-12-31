import json
import logging
import time

from datetime import datetime, timedelta
from functools import wraps

import requests.utils
from flask import redirect, url_for, abort, jsonify, flash, request, session
from flask_login import current_user, logout_user

from edutalk.config import config
from edutalk.models import User, AccessToken
from edutalk.exceptions import CCMAPIError
from edutalk.redis_config import redisClient

log = logging.getLogger('edutalk.utils')


def login_required(f):
    '''
    Ref: http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/#login-required-decorator

    the decorated function will be passed a kwarg: ``user``, an instance of
    models.User
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            session['next'] = request.path
            return redirect(url_for('root.account.auth_redirect_endpoint'))

        accesstoken_record = \
            (config.db.session
             .query(AccessToken)
             .filter_by(user_id=current_user.id)
             .first())

        timestamp=datetime.now().timestamp()
        redisClient.zadd('online_user', {current_user.id: timestamp})
        '''if current_user.approved:
            last_active = f"user:last_active:{current_user.id}"
            redisClient.set(last_active, datetime.utcnow().timestamp())
            redisClient.expire(last_active, timedelta(minutes=5))

        if not redisClient.exists(last_active):
            pass'''

        if not accesstoken_record:
            logout_user()
            session['next'] = request.path
            return redirect(url_for('root.account.auth_redirect_endpoint'))

        if not current_user.approved:
            if f.__name__ != 'index':
                return redirect(url_for('root.index'))
            flash('Please wait for administrator\'s approval', 'error')
        return f(*args, **kwargs)
    return wrapper


def teacher_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_teacher and not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def json_err(reason: str, **others):
    x = {'state': 'error', 'reason': reason}
    x.update(others)
    return jsonify(x)


def ag_ccmapi(u_id, op, payload={}):
    '''
    :param u_id: Owner ID of iottalk data.
    :param op: The CCMAPI name which AutoGen support, e.g. 'account.login'
    :param payload: Data that should be provided to CCMAPI.
    :type u_id: int
    :type op: string
    :type payload: dict.
    '''
    try:
        # Check User
        user = User.query.get(u_id)
        if user is None:
            raise Exception(f"User not found, u_id: {u_id}")
        db = config.db
        url = config.ag_url + '/ccm_api/'
        accesstoken_record = \
            (db.session
             .query(AccessToken)
             .filter_by(user_id=u_id)
             .order_by(AccessToken.expires_at.desc())
             .first())
        if accesstoken_record.expires_at - datetime.utcnow() < timedelta(minutes=5):
            accesstoken_record.refresh()
            accesstoken_record = \
                (db.session
                 .query(AccessToken)
                 .filter_by(user_id=u_id)
                 .order_by(AccessToken.expires_at.desc())
                 .first())
        data = {
            "access_token": accesstoken_record.token,
            "api_name": op,
            "payload": payload
        }
        # start = time.time()
        res = user.ccm_session.post(url, json=data)
        cookies = requests.utils.dict_from_cookiejar(res.cookies)
        if cookies != user.cookies:
            db.session.begin_nested()
            user.cookies = cookies
            db.session.commit()
            # log.info("ag ccm cookies: "+str(cookies))
        # log.info("ag ccm api ["+op+"] takes: "+str(time.time()-start))
        if res.status_code // 100 != 2:
            log.error(f"CCM API error for operation {op}: Status {res.status_code}, Response: {res.text}")
            raise CCMAPIError(res.text)
        
        try:
            result = json.loads(res.text).get('result')
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error in ag_ccmapi for operation {op}: {str(e)}")
            raise CCMAPIError(f"JSON decode error: {str(e)}")
        
        return result

    except requests.exceptions.RequestException as e:
        log.error(f"Network error in ag_ccmapi for operation {op}: {str(e)}")
        raise CCMAPIError(f"Network error: {str(e)}")

    except Exception as e:
        log.error(f"Unexpected error in ag_ccmapi for operation {op}: {str(e)}")
        raise CCMAPIError(f"Unexpected error: {str(e)}")


def refresh_users_tokens():
    db = config.db
    users = User.query.all()
    for user in users:
        accesstoken_record = \
            (db.session
             .query(AccessToken)
             .filter_by(user_id=user.id)
             .order_by(AccessToken.expires_at.desc())
             .first())
        if accesstoken_record.expires_at - datetime.utcnow() < timedelta(days=3):
            log.info('refreshing tokens of user '+str(user.id))
            accesstoken_record.refresh()
