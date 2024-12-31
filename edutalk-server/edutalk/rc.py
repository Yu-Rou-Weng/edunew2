import logging
import re

from flask import Blueprint, render_template, session, abort, request, redirect, url_for
from flask_login import login_user, current_user

from edutalk import device
from edutalk.config import config
from edutalk.models import LectureProject, Lecture, User
from edutalk.utils import login_required

import json

app = Blueprint('rc', __name__)
db = config.db
log = logging.getLogger('edutalk.rc')



@app.route('/', methods=['GET'], strict_slashes=False)
def index(lec_id):
    token = request.args.get('token')
    
    log.info(f"Received request for RC page with lec_id: {lec_id}, token: {token}")

    # 检查 token 和用户登录情况
    if not token and 'uid' not in session:  # 没有 token 且用户未登录
        log.warning(f"Token and session missing for lec_id: {lec_id}, redirecting to login.")
        session['next'] = request.path
        return redirect(url_for('root.account.auth_redirect_endpoint'))

    elif not token and 'uid' in session:  # 没有 token，但用户已经登录
        user = User.query.get(session.get('uid'))
        log.info(f"User {user.username} already logged in.")

    elif token:  # 使用 token 进行用户验证
        user = User.query.filter_by(_token=token).first()
        if user is None:
            log.error(f"Invalid token for lec_id: {lec_id}")
            return '''<h2>Token invalid</h2>''', 403

        session.clear()
        login_user(user)
        log.info(f"User {user.username} logged in with token.")

    # 查找课程和 LectureProject
    lecture = Lecture.query.get(lec_id)
    if lecture is None:
        log.error(f"Lecture with id {lec_id} not found.")
        abort(404)

    x = LectureProject.get_by_lec_user(lecture, user)
    if x is None:
        log.error(f"No LectureProject found for lecture {lec_id} and user {user.username}.")
        abort(404)

    log.info(f"LectureProject found for lec_id {lec_id} and user {user.username}.")

    # 处理 df_list 和 idf_list
    df_list = {re.sub(r'_', r'-', x['df_name']): x for x in x.ido['df_list']}
    idf_list = list(set([df for df in df_list]))

    idfs = []
    exclude_idfs = []
    for odf in lecture.joins:
        for idf in lecture.joins[odf]:
            if not re.search("Number-I[0-9]*$", idf[0]) and not re.search("RangeSlider-I[0-9]*$", idf[0]) and not \
                    idf[0] in ("EduAcc-I", "EduAlc-I", "EduGyr-I", "EduHum-I", "EduMag-I", "EduOri-I", "EduUV-I"):
                exclude_idfs.append(re.sub(r'-', r'_', idf[0]))
            idfs.append([re.sub(r'-', r'_', idf[0]), idf[2]])

    # todo: add if you have others
    bind_callbacks = [url_for("root.m2.bind", lec_id=lecture.id, d_id="", _external=True)]
    log.info('iv_list content: %s', lecture.iv_list)
    # 判断是否为 app 请求，返回 JSON 数据
    if request.args.get('app', default=False, type=lambda v: v.lower() == 'true'):
        log.info(f"Returning JSON response for app mode for lecture {lec_id}.")
        return json.dumps({
            'lecture': lecture.id,
            'idfs': idfs,
            'exclude_idfs': exclude_idfs,
            'idf_list': [[df, ['magic']] for df in idf_list],
            'csm_url': config.csm_url(),
            'dm_name': lecture.idm,
            'dev': '{}.{}'.format(user.username, lecture.idm),
            'iv_list': lecture.iv_list,
            "rc_bind": url_for("root.rc.bind", lec_id=lecture.id, d_id="", _external=True),
            "bind_callbacks": bind_callbacks
        })
    else:
        log.info(f"Rendering RC page for lecture {lec_id}.")
        return render_template('rc/index.html',
                               lecture=lecture,
                               idfs=idfs,
                               idf_list=[[df, ['magic']] for df in idf_list],
                               csm_url=config.csm_url(),
                               dm_name=lecture.idm,
                               dev='{}.{}'.format(user.username, lecture.idm),
                               iv_list=lecture.iv_list,
                               bind_callbacks=bind_callbacks,
                               exclude_idfs=exclude_idfs)


@app.route('/bind/<string:d_id>', methods=['POST'], strict_slashes=False)
@login_required
def bind(lec_id, d_id):
    lec = Lecture.query.get(lec_id)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    do_id = x.ido['do']['do_id']
    return device.graceful_bind(x, do_id, d_id)


@app.route('/unbind/', methods=['POST'], strict_slashes=False)
@login_required
def unbind(lec_id):
    lec = Lecture.query.get(lec_id)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    do_id = x.ido['do']['do_id']
    return device.unbind(x, do_id)
