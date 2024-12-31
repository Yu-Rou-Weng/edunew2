import code
import logging
import os
import shutil
import sys

import iot

from argparse import ArgumentParser
from pkg_resources import iter_entry_points
from threading import Thread

from pony import orm

from iot import version
from iot.config import config
from iot.models import db_init

log = logging.getLogger('iottalk')


def parse_args():
    plugins = load_plugins()
    parser = ArgumentParser(description='IoTtalk controller')
    subparsers = parser.add_subparsers(help='available sub-commands')

    parser.add_argument(
        '-d', '--debug',
        dest='debug',
        action='store_true',
        default=False,
        help='debug mode')
    parser.add_argument(
        '-c', '--config',
        dest='ini_path',
        default=None,
        help='IoTtalk ini config file',
    )
    parser.add_argument(
        '--version',
        action='version',
        version='IoTtalk {}'.format(version))

    # sub command: ``initdb``
    initdb_parser = subparsers.add_parser('initdb', help='initialize database')
    initdb_subparser = initdb_parser.add_subparsers(help='available servers')
    load_initdb_parser(plugins, initdb_subparser)
    # sub command: ``start``
    start_parser = subparsers.add_parser('start', help='start server')
    start_subparser = start_parser.add_subparsers(help='available servers')
    start_csm_parser = start_subparser.add_parser('csm', help='start csm server')
    start_csm_parser.set_defaults(func=handle_start_csm)
    load_start_parser(plugins, start_subparser)
    # sub command: ``shell``
    shell_parser = subparsers.add_parser('shell', help=(
        'start a python interactive shell with db ready enviroment'))
    shell_parser.set_defaults(func=iotctl_shell)
    # sub command: ``genconf``
    genconf_parser = subparsers.add_parser(
        'genconf', help='get a copy of sample ini config')
    genconf_parser.add_argument('dest', type=str, help='destination path')
    genconf_parser.set_defaults(func=handle_genconf)

    return parser, parser.parse_args()


def main(init_only=False):
    parser, args = parse_args()
    handle_debug(args)
    handle_ini_file(args)

    if init_only:  # for the case of esm forkserver
        return

    if hasattr(args, 'func'):
        return args.func(args)

    parser.print_help()


def handle_debug(args):
    '''
    :param args: the namespace obj from ``ArgumentParser``
    '''
    config.debug = args.debug

    logging.basicConfig(level=config.logging_level)
    orm.sql_debug(False)


def handle_ini_file(args):
    if args.ini_path:
        config.read_config(args.ini_path)
    # load configs for plugins
    plugins = load_plugins()
    load_plugins_func('load_config', plugins, args)


def handle_start_csm(args):
    '''
    :param args: the namespace obj from ``ArgumentParser``
    '''
    from iot.csm.server import main as csm_server
    from iot.raproto.http import main as http_app

    t = Thread(target=http_app)
    t.daemon = True
    t.start()
    csm_server()


def list_apps(filter_=lambda r: True):
    '''
    :param filter_: the filter function
    '''
    return config.db.Resource.select(filter_)[:]


def deregister_apps(apps):
    '''
    :param apps: the ``config.db.Resource`` object obtained from list_apps()
    :type apps: Iterable[config.db.Resource]
    '''
    for app in apps:
        app.delete()


def iotctl_shell(args):
    '''
    Start a python shell with the db setup.

    If the IPython is available, we will invoke IPython embed shell.
    '''
    banner = (
        'IoTtalk shell has following variables available:\n'
        '    config:          the iot.config.config object .\n'
        '    db:              config.db\n'
        '    iot:             the iottalk core package.\n'
        '    list_apps:       the function that lists all registered apps\n'
        '    deregister_apps: the function that deregisters specified apps')

    locals_ = {
        'config': config,
        'db': config.db,
        'iot': iot,
        'list_apps': list_apps,
        'deregister_apps': deregister_apps,
    }

    db_init()

    with orm.db_session:
        try:
            import IPython
        except ImportError:
            pass
        else:
            return IPython.embed(
                argv=sys.argv[2:], header='{}'.format(banner), user_ns=locals_,
                # https://github.com/ipython/ipython/issues/11523#issuecomment-521434789
                colors='neutral')

        # fallback to builtin interactive shell
        cprt = ('Type "help", "copyright", "credits" or "license" '
                'for more information.')
        py_banner = 'Python {ver} on {platform}\n{cprt}\n\n{iottalk}'.format(
            ver=sys.version, platform=sys.platform, cprt=cprt, iottalk=banner)
        code.interact(banner=py_banner, local=locals_)


def handle_genconf(args):
    prefixes = [
        os.path.join(sys.prefix, 'share', 'iottalk'),
        os.path.join(os.path.dirname(__file__), '..', 'share')]
    for prefix in prefixes:
        src = os.path.join(prefix, 'iottalk.ini.sample')
        if os.path.isfile(src):
            break
    else:
        raise OSError('sample ini not found')
    dest = args.dest
    shutil.copy(src, dest)

    plugins = load_plugins()
    plugins_genconf(plugins, dest)


def load_plugins():
    return [mod.load() for mod in iter_entry_points('iot.cli')]


def load_start_parser(*args):
    return load_plugins_func('add_start_parser', *args)


def load_initdb_parser(*args):
    return load_plugins_func('add_initdb_parser', *args)


def load_plugins_func(cmd, plugins, *args):
    ret = []
    for mod in plugins:
        if cmd not in dir(mod):
            continue
        ret.append(getattr(mod, cmd)(*args))
    return ret


def plugins_genconf(plugins, dest):
    confs = load_plugins_func('genconf', plugins)
    with open(dest, 'a') as f:
        for conf in confs:
            f.write('\n')
            f.write(conf)


if __name__ == '__main__':
    main()
