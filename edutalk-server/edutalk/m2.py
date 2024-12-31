from flask import Blueprint, abort
from edutalk.models import LectureProject, Lecture
from edutalk import device
from flask_login import current_user
from edutalk.config import config
from edutalk.utils import login_required

app = Blueprint('m2', __name__)
db = config.db

m2_idm_name = 'M2'


# use optional d_id, provide d_id if use replay device, else use shared m2 device
@app.route('/bind/', defaults={'d_id': None}, methods=['POST'], strict_slashes=False)
@app.route('/bind/<string:d_id>', methods=['POST'], strict_slashes=False)
@login_required
def bind(lec_id, d_id):
    lec = Lecture.query.get(lec_id)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    m2_do_id = x.m2_ido['do']['do_id']

    # bind specific m2 for replay
    if d_id:
        return device.graceful_bind(x, m2_do_id, d_id)

    # bind shared m2, this should be after rc bind
    # because the binding order with multiple device
    # on one join function will affect the input order
    # currently we can only have one m2 device
    for iv in lec.iv_list:
        for param in iv['params']:
            if param['model'] == 'M2' and param['mac_addr']:
                d_id = param['mac_addr']
                break
        else:
            continue
        break
    return device.graceful_bind(x, m2_do_id, d_id)


@app.route('/unbind/', methods=['POST'], strict_slashes=False)
@login_required
def unbind(lec_id):
    lec = Lecture.query.get(lec_id)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    m2_do_id = x.m2_ido['do']['do_id']

    # unbind m2
    return device.unbind(x, m2_do_id)
