from flask import Blueprint, abort, jsonify, request
from edutalk.models import Lecture, LectureProject, Comment, User
from flask_login import current_user
from edutalk.config import config
from edutalk.utils import login_required, teacher_required

app = Blueprint('comment', __name__)
db = config.db


@app.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    if x is None:
        abort(404)

    comment = x.comment
    if comment is None:
        comment = Comment(project=x)
        db.session.add(comment)
        db.session.commit()

    return jsonify({'comment': comment.content})


@app.route('/comment/student/<string:u_id>', methods=['GET'], strict_slashes=False)
@login_required
@teacher_required
def get_comment(lec_id, u_id):
    lecture = Lecture.query.get(lec_id)
    student = User.query.get(u_id)
    if student is None or student.group.name != 'student':
        abort(404)

    x = LectureProject.get_by_lec_user(lecture, student)
    if x is None:
        abort(404)

    comment = x.comment
    if comment is None:
        comment = Comment(project=x)
        db.session.add(comment)
        db.session.commit()

    return jsonify({'comment': comment.content})


@app.route('/comment/student/<string:u_id>', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def save_comment(lec_id, u_id):
    lecture = Lecture.query.get(lec_id)
    student = User.query.get(u_id)
    if student is None or student.group.name != 'student':
        abort(404)

    x = LectureProject.get_by_lec_user(lecture, student)
    if x is None:
        abort(404)

    comment = x.comment
    if comment is None:
        comment = Comment(project=x)
        db.session.add(comment)

    content = request.json.get('comment')
    if content is None or not type(content) == str:
        abort(400)
    comment.content = content
    db.session.commit()

    return jsonify({'state': 'ok'})
