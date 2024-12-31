import hashlib
import logging

from sqlalchemy import and_

from iotgui import config
from iotgui.db import model

log = logging.getLogger("{}ccm.api.auth\033[0m".format(config.LOG_COLOR_GUI))


def encrypt_password(x: str):
    if x is None:
        return

    sha512 = hashlib.sha512()
    sha512.update(config.FLASK_SECRET_KEY.encode() + x.encode())
    return sha512.hexdigest()


def auth(username, password, db_session) -> model.User or None:
    password = encrypt_password(password)
    return (
        db_session.query(model.User)
                  .filter(and_(
                      model.User.u_name == username,
                      model.User.passwd == password))
                  .first())
