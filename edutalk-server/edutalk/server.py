import os

from flask import Flask, Blueprint, render_template, jsonify, send_from_directory
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix
from time import sleep

from edutalk.config import config
from edutalk.models import Lecture, User

from edutalk.utils import login_required, json_err, refresh_users_tokens
from edutalk.account import app as account_app
from edutalk.lecture import app as lecture_app
from edutalk.vp import app as vp_app
from edutalk.rc import app as rc_app
from edutalk.m2 import app as m2_app
from edutalk.video import app as video_app
from edutalk.demo import app as demo_app
from edutalk.comment import app as comment_app
from edutalk.oauth2_client import oauth2_client

from flask_apscheduler import APScheduler
from datetime import datetime, timedelta

app = Flask(__name__, static_url_path=config.web_server_prefix + '/static')
root = Blueprint('root', __name__)
scheduler = APScheduler()
scheduler.init_app(app)
app.config['WTF_CSRF_ENABLED'] = False
@app.after_request
def add_csrf_header(response):
    response.headers.set('X-CSRFToken', generate_csrf())
    return response
    
@scheduler.task('interval', id='refresh_users_tokens', seconds=300,
                next_run_time=datetime.now()+timedelta(seconds=30))
def refresh_users():
    with scheduler.app.app_context():
        refresh_users_tokens()

scheduler.start()

@root.route('/')
def intermediate():
    return render_template('intermediate.html')

@root.route('/genai')
@login_required
def index():
    return render_template('homepage.html',
                           new_admin=config.new_admin,
                           lesson_data=Lecture.list_())

@root.route('/csrf_refresh/', methods=['GET'])
@login_required
def csrf_refresh():
    return jsonify(generate_csrf())

@root.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.url_defaults
def static_file_timestamp(endpoint, values):
    if endpoint != 'static':
        return

    fname = values.get('filename')
    if not fname:
        return

    path = os.path.join(os.path.dirname(__file__), 'static', fname)
    values['_t'] = round(os.path.getmtime(path))

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return json_err(e.description), 400

def setup_db():
    if config.db_conf['type'] == 'sqlite':
        db_url = 'sqlite:///{}'.format(
            os.path.join(config.userdir, config.db_conf['url']))
    else:
        db_url = 'mysql+mysqlconnector://{user}:{passwd}@{host}:{port}/{db}'.format(
            user=config.db_conf['user'],
            passwd=config.db_conf['passwd'],
            host=config.db_conf['host'],
            port=config.db_conf['port'],
            db=config.db_conf['url'],
        )

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    config.app = app
    config.db.create_all(app=app)

@app.context_processor
def deeplinkURL():
    return dict(deeplinkURL=config.deeplink)

def main():
    root.register_blueprint(account_app, url_prefix='/account')
    root.register_blueprint(lecture_app, url_prefix='/lecture')
    root.register_blueprint(vp_app, url_prefix='/lecture/<int:lec_id>/vp')
    root.register_blueprint(rc_app, url_prefix='/lecture/<int:lec_id>/rc')
    root.register_blueprint(m2_app, url_prefix='/lecture/<int:lec_id>/m2')
    root.register_blueprint(video_app, url_prefix='/lecture/<int:lec_id>/video')
    root.register_blueprint(demo_app, url_prefix='/demo')
    root.register_blueprint(comment_app, url_prefix='/lecture/<int:lec_id>/grading')
    app.register_blueprint(root, url_prefix=config.web_server_prefix)

    setup_db()
    app.config['SECRET_KEY'] = config.secret_key
    
    if bool(config.proxy_used):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    login_manager = LoginManager()
    login_manager.init_app(app)
    oauth2_client.init_app(app)

    oauth2_client.register(
        name='iottalk',
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=config.discovery_endpoint,
        client_kwargs={'scope': 'openid', }
    )

    app.config['WTF_CSRF_TIME_LIMIT'] = 60 * 60
    CSRFProtect(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter_by(id=user_id).first()

    from iottalkpy import dai
    for _ in range(5):
        try:
            dai.module_to_sa(dai.load_module(
                '/edutalk-server/edutalk/simple_logger.py')).start()
        except ConnectionResetError:
            sleep(1)
            continue
        else:
            break

    app.run(
        host=config.bind,
        port=config.http_port,
        threaded=True,
        debug=config.debug,
    )

if __name__ == '__main__':
    main()