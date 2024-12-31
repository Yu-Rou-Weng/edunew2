import logging
import os
import signal
import subprocess
import sys

from argparse import ArgumentParser

from wait4it import (
    wait_for,
    WaitForTimeoutError,
)

from iotgui.signal_handlers import (
    handle_signal_for_gunicorn,
    SIGNALS_USED_BY_GUNICORN,
)

logger = logging.getLogger(__name__)


def main():
    parser = ArgumentParser(description='IoTtalk gui controller')
    subparsers = parser.add_subparsers(help='available sub-commands')

    # db sub commands
    db_parser = subparsers.add_parser('db', help='db management')
    db_subparser = db_parser.add_subparsers(help='available db sub-commands')

    # create db
    db_create_parser = db_subparser.add_parser(
        'create',
        help='create db without default value')
    db_create_parser.set_defaults(func=create_db)

    # import db
    db_import_parser = db_subparser.add_parser('import', help='import data from json')
    db_import_parser.add_argument(
        'jsonfile',
        nargs='+',
        type=str,
        help='the import json file')
    db_import_parser.set_defaults(func=import_db)

    # init db
    db_init_parser = db_subparser.add_parser(
        'init',
        help='initialize database (create and use default value)')
    db_init_parser.set_defaults(func=init_db)

    # start server
    start_parser = subparsers.add_parser('start', help='start the iottalk2 ccm/gui server')
    start_subparser = start_parser.add_subparsers(help='available start sub-commands')
    add_start_parser(start_subparser)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        load_config(args)
        return args.func(args)

    parser.print_help()


def load_config(args):
    if not hasattr(args, 'ini_path') or not args.ini_path:
        return

    from iotgui import config

    config.read_config(args.ini_path)


def create_db(args):
    from iotgui.db import create

    create()


def import_db(args):
    import json
    from iotgui.db.import_ import import_data

    for filename in args.jsonfile:
        try:
            with open(filename, 'r') as f:
                import_data(json.load(f))
        except Exception:
            print('import error', filename)


def init_db(args):
    from iotgui.db import reset

    reset()


def start_ccm(args):
    from iotgui import config

    if config.ENABLE_MQTT_AUTH:
        # Wait until the AA Subsystem is available
        try:
            wait_for(host=config.AA_HOST, port=int(config.AA_PORT), timeout=15)
        except WaitForTimeoutError:
            logger.error('The AA Subsystem is unavailable, CCM is terminating')
            sys.exit(1)

    if args.wsgi:  # When using WSGI mode
        # Reset signal handlers
        for signal_number in SIGNALS_USED_BY_GUNICORN:
            signal.signal(signal_number, signal.SIG_IGN)
        # Install the desired signal handlers
        for signal_number in SIGNALS_USED_BY_GUNICORN:
            signal.signal(signal_number, handle_signal_for_gunicorn)

        subprocess.run([
            # Gunicorn options.
            #
            # Ref: https://docs.gunicorn.org/en/latest/settings.html
            'gunicorn',
            '-b',  # Specify listening address
            '{}:{}'.format(config.CCM_HOST, config.CCM_PORT),
            '--access-logfile',
            '-',
            '--pid',  # Specify the path of the pid file
            config.GUNICORN_PID_FILE_NAME,
            # Ref: https://docs.gunicorn.org/en/latest/run.html#gunicorn
            'iotgui.wsgi:get_application(ini_path={!r})'.format(args.ini_path),
        ])
    else:
        from iotgui.ccm.server import main as flask_main

        wsgi_app()  # setup configs
        flask_main()  # start dev server


def load_flask_config(app):
    import datetime

    from iotgui import config, db
    from iotgui.ccm import mqttclient

    app.secret_key = config.FLASK_SECRET_KEY
    app.config['SESSION_REFRESH_EACH_REQUEST'] = False
    app.permanent_session_lifetime = datetime.timedelta(minutes=config.SESSION_TIME_OUT)

    # For integrating with flask auto reloader in debug mode.
    # Without this hook, flask debug mode will start duplicated mqtt clients.
    @app.before_first_request
    def f():
        db.migrate()
        db.connect()
        mqttclient.init()

    return app


def wsgi_app():
    from iotgui.ccm.server import app as flask_app

    load_flask_config(flask_app)
    return flask_app


def start_gui(args):
    from iotgui.ccm.server import main
    from iotgui.ccm.server import app as flask_app

    load_flask_config(flask_app)
    main()


def add_start_parser(start_subparser):
    # start ccm
    start_ccm_parser = start_subparser.add_parser('ccm', help='start ccm server')
    start_ccm_parser.set_defaults(func=start_ccm)
    start_ccm_parser.add_argument(
        '-w', '--wsgi',
        dest='wsgi',
        action='store_true',
        default=False,
        help='wsgi application mode',
    )

    # start gui
    start_gui_parser = start_subparser.add_parser('gui', help='start gui server')
    start_gui_parser.set_defaults(func=start_gui)


def add_initdb_parser(initdb_subparser):
    initdb_ccm_parser = initdb_subparser.add_parser('ccm', help='init ccm db')
    initdb_ccm_parser.set_defaults(func=init_db)


def genconf():
    """
    return the string of sample config.

    This function will be called by command ``iotctl`` in ``iot.cli``.
    """
    prefixes = [
        os.path.join(sys.prefix, 'share', 'iottalk'),  # production installation
        os.path.join(os.path.dirname(__file__), '..', 'share'),  # for dev mode
    ]
    for prefix in prefixes:
        src = os.path.join(prefix, 'iottalk-gui.ini.sample')
        if os.path.isfile(src):
            break
    else:
        raise OSError('sample ini file not found')

    with open(src) as f:
        return f.read()


if __name__ == '__main__':
    main()
