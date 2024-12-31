import logging

from flask import Blueprint, render_template, abort, jsonify, request
from flask_login import current_user

from edutalk import device
from edutalk.config import config
from edutalk.models import LectureProject, Lecture, User, Group
from edutalk.utils import login_required, ag_ccmapi, teacher_required

app = Blueprint('vp', __name__)
db = config.db
log = logging.getLogger('edutalk.vp')


@app.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    if x is None:
        abort(404)

    odfs = []
    for iv in lecture.iv_list:
        units = []
        for param in iv['params']:
            units.append(param['unit'])
        odfs.append(['{}{}_O{}'.format(lecture.odm, iv['giv_name'], iv['index']), units])

    return render_template('vp/index.html',
                           lecture=lecture,
                           dm_name=lecture.odm,
                           iv_list=lecture.iv_list,
                           odf_list=odfs,
                           idf_list=[x['idf'] for x in lecture.output_variables],
                           output_variables=lecture.output_variables,
                           csm_url=config.csm_url(),
                           dev='{}.{}'.format(current_user.username, lecture.odm))


@app.route('/code', methods=['GET'], strict_slashes=False)
@login_required
def code(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    log.info('lecture: {}'.format(x))
    if x is None:
        abort(404)
    return jsonify({'name': x.lecture.da_name, 'code': x.code})


@app.route('/students', methods=['GET'], strict_slashes=False)
@login_required
@teacher_required
def students(lec_id):
    students = []
    for p in LectureProject.query.filter_by(lec_id=lec_id).all():
        if p.user.group.name == 'student':
            students.append({'id': p.user.id, 'username': p.user.username})
    return jsonify(students)


@app.route('/code/student/<string:u_id>', methods=['GET'], strict_slashes=False)
@login_required
@teacher_required
def student_code(lec_id, u_id):
    lecture = Lecture.query.get(lec_id)
    student = User.query.get(u_id)
    if student is None or student.group.name != 'student':
        abort(404)
    x = LectureProject.get_by_lec_user(lecture, student)
    if x is None:
        abort(404)
    return jsonify({'name': x.lecture.da_name, 'code': x.code})


@app.route('/code', methods=['POST'], strict_slashes=False)
@login_required
def code_update(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    if x is None:
        abort(404)

    code = request.json.get('code')
    if not code:
        abort(400)

    x.code = code
    db.session.commit()

    return jsonify({'state': 'ok'})


@app.route('/code/student/<string:u_id>', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def student_code_update(lec_id, u_id):
    lecture = Lecture.query.get(lec_id)
    student = User.query.get(u_id)
    if student is None or student.group.name != 'student':
        abort(404)

    x = LectureProject.get_by_lec_user(lecture, student)
    if x is None:
        abort(404)

    code = request.json.get('code')
    if not code:
        abort(400)

    x.code = code
    db.session.commit()

    return jsonify({'state': 'ok'})


@app.route('/code/reset', methods=['POST'], strict_slashes=False)
@login_required
def code_reset(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    if x is None:
        abort(404)

    x.code = lecture.code
    db.session.commit()

    return jsonify({'state': 'ok', 'code': x.code})


@app.route('/code/reset/<string:u_id>', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def student_code_reset(lec_id, u_id):
    lecture = Lecture.query.get(lec_id)
    student = User.query.get(u_id)
    if student is None or student.group.name != 'student':
        abort(404)

    x = LectureProject.get_by_lec_user(lecture, student)
    if x is None:
        abort(404)

    x.code = lecture.code
    db.session.commit()

    return jsonify({'state': 'ok', 'code': x.code})


@app.route('/code/default', methods=['POST'], strict_slashes=False)
@login_required
def code_default(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    if x is None:
        abort(404)

    lecture.code = x.code
    db.session.commit()

    return jsonify({'state': 'ok'})


@app.route('/code/default/<string:u_id>', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def student_code_default(lec_id, u_id):
    lecture = Lecture.query.get(lec_id)
    student = User.query.get(u_id)
    if student is None or student.group.name != 'student':
        abort(404)

    x = LectureProject.get_by_lec_user(lecture, student)
    if x is None:
        abort(404)

    lecture.code = x.code
    db.session.commit()

    return jsonify({'state': 'ok'})


@app.route('/bind/<string:d_id>', methods=['POST'], strict_slashes=False)
@login_required
def bind(lec_id, d_id):
    lec = Lecture.query.get(lec_id)

    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    # no need for actuators
    if len(lec.output_variables) == 0:
        do_id = x.odo['do']['do_id']
        return device.graceful_bind(x, do_id, d_id)

    # lock
    if db.session.bind.name == 'sqlite':
        db.session.execute('begin immediate transaction')
    lec = Lecture.query.with_for_update().get(lec_id)

    pre = LectureProject.get_by_lec_user_last_bind(lec, current_user)
    msg = ''
    code = 200
    actuator_errors = []
    output_device = ag_ccmapi(x.u_id, 'device.get',
                              {'p_id': x.p_id, 'do_id': x.odo['do']['do_id']})
    if (pre != x) and \
            ((len(output_device) == 1 and output_device[0]['mac_addr'] != d_id) or
             len(output_device) > 1):
        msg = 'Actuators are disabled for you ' \
              'because someone is still using this lecture !'
    else:
        # unbind actuators in last binding lecture project
        if pre and pre != x:
            pre.unbind_actuators()
            pre.last_bind = False
        x.last_bind = True
        # bind actuators
        # todo: based on joins
        if len(lec.output_variables) > 0:
            actuators_do_id = [x['do_id'] for x in x.actuators_do]
            i = 0
            for actuator_var in lec.output_variables:
                if actuator_var['actuator']:
                    do_id = actuators_do_id[i]
                    i += 1
                    if actuator_var['mac_addr']:
                        res, c = device.graceful_bind(x, do_id, actuator_var['mac_addr'],
                                                      max_retry=1)
                        if c != 200:
                            actuator_errors \
                                .append('Actuator {} with mac_addr {} is not online !'
                                        .format(actuator_var['actuator'],
                                                actuator_var['mac_addr']))
                else:
                    continue

    _, c = device.graceful_bind(x, x.odo['do']['do_id'], d_id)
    if (msg or len(actuator_errors) > 0) and c == 200:
        code = 400
    elif c != 200:
        msg, code = '', 400

    db.session.commit()
    return jsonify({'message': msg, 'actuator_errors': actuator_errors}), code


'''@app.route('/unbind/', methods=['POST'], strict_slashes=False)
@login_required
def unbind(lec_id):
    lec = Lecture.query.get(lec_id)

    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    if len(lec.output_variables) == 0:
        return device.unbind(x, x.odo['do']['do_id'])

    # lock
    if db.session.bind.name == 'sqlite':
        db.session.execute('begin immediate transaction')
    Lecture.query.with_for_update().get(lec_id)

    x.unbind_actuators()
    x.last_bind = False
    res = device.unbind(x, x.odo['do']['do_id'])

    db.session.commit()
    return res'''
@app.route('/unbind/', methods=['POST'], strict_slashes=False)
@login_required
def unbind(lec_id):
    try:
        lec = Lecture.query.get(lec_id)
        if lec is None:
            return jsonify({'error': 'Lecture not found'}), 404

        x = LectureProject.get_by_lec_user(lec, current_user)
        if x is None:
            return jsonify({'error': 'LectureProject not found'}), 404

        do_id = x.odo['do']['do_id']
        result = device.unbind(x, do_id)
        
        if isinstance(result, tuple):
            return result
        
        return jsonify({'message': 'Successfully unbound'}), 200
    except Exception as e:
        log.error(f"Error in unbind: {str(e)}")
        return jsonify({'error': 'An error occurred during unbind'}), 500
