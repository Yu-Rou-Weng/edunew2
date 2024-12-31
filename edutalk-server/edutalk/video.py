from flask import Blueprint, abort,  render_template
from edutalk.models import LectureProject, Lecture
from edutalk import device
from flask_login import current_user
from edutalk.config import config
from edutalk.utils import login_required

app = Blueprint('video', __name__)
db = config.db


@app.route('/stream/', methods=['GET'], strict_slashes=False)
@login_required
def index(lec_id):
    lec = Lecture.query.get(lec_id)
    if lec is None:
        abort(404)
    # todo: read ws_uri from config
    return render_template('kurento/index.html',
                           ws_uri=config.kurento_server_url,
                           video_url=lec.video)
