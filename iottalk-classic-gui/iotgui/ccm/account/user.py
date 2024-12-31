import logging
import uuid

import flask_login

from iotgui import config
from iotgui.ccm.account.verify import encrypt_password
from iotgui.db import model

from .oauth2 import revoke_access_token

log = logging.getLogger("{}ccm.auth\033[0m".format(config.LOG_COLOR_GUI))


def login_user(user: model.User, http_session, redis):
    http_session['session_id'] = str(uuid.uuid4())
    flask_login.login_user(user)
    log.info('User %r logs in', flask_login.current_user.u_name)
    log.debug('redis-hset: u_id: %s, session: %s',
              http_session['user_id'], http_session['session_id'])
    redis.hset('user', http_session['session_id'], http_session['user_id'])


def logout_user(http_session, redis):
    if config.OAUTH2_CLIENT_ID:
        revoke_access_token(http_session)

    # remove user data cache from redis
    if http_session.get('session_id'):
        redis.hdel('user', http_session['session_id'])

    # logout user
    log.info('User %r logs out', flask_login.current_user.u_name)
    flask_login.logout_user()
    http_session.clear()


def create(db_session, username, password, **kwargs) -> model.User:
    u = model.User(u_name=username, passwd=encrypt_password(password), **kwargs)
    db_session.add(u)
    db_session.commit()
    return u


def is_exist(db_session, username: str) -> bool:
    '''
    check username exists or not.
    '''
    return (
        db_session.query(model.User)
                  .filter(model.User.u_name == username)
                  .first()
    ) is not None


def delete(db_session, http_session, redis):
    user = db_session.query(model.User).get(http_session['user_id'])
    logout_user(http_session, redis)
    db_session.delete(user)
    db_session.commit()


def change_password(db_session, u_id, new_pass):
    '''
    Note: This function should only call by Admin.
    '''
    c = (db_session.query(model.User)
                   .filter(model.User.u_id == u_id)
                   .update({'passwd': encrypt_password(new_pass)}))
    db_session.commit()

    return c == 1


def set_admin(db_session, u_id, is_admin: bool):
    '''
    Note: This function should only call by Admin.
    '''
    c = (db_session.query(model.User)
                   .filter(model.User.u_id == u_id)
                   .update({'is_admin': is_admin}))
    db_session.commit()

    return c == 1
