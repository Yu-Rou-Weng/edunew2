from flask import Blueprint, render_template, abort
from flask_login import current_user

from edutalk.config import config
from edutalk.models import Lecture, LectureProject
from edutalk.utils import login_required, ag_ccmapi

app = Blueprint('demo', __name__)
db = config.db


@app.route('/', methods=['GET'], strict_slashes=False)
@login_required
def index():
    '''
    A placeholder for url_for
    '''
    abort(403)


@app.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@login_required
def refresh(id_):
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    df_list = tuple(map(    # output device feature list
        lambda x: x.get('df_name'),
        ag_ccmapi(current_user.id, 'devicemodel.get', {'key': lec.odm})['df_list']))
    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        LectureProject.create(lec, current_user)

    return render_template("demo.html",
                           lecture=lec,
                           df_list=df_list,
                           lesson_data=Lecture.list_(),
                           token=current_user.token)
