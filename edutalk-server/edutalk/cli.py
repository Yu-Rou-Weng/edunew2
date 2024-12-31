import os
import shutil
import sys
import requests

from argparse import ArgumentParser

import yaml

from edutalk import models
from edutalk.config import config
from edutalk.models import User, Group
import edutalk.aaa_api_client as aaa_api_client
from edutalk.exceptions import CCMAPIError
from functools import partial
import json


def load_fixtures_and_create_admin(fname):
    from edutalk.server import setup_db
    setup_db()
    db = config.db

    with open(fname) as f, config.app.app_context():
        # detect whether admin user is in db for initdb check
        if len(db.session.query(User).all()) != 0:
            print("skip initdb, you have to delete dbs of edutalk and iottalk-gui"
                  " for re-initialization !")
            return

        for x in yaml.load(f):
            if 'model' in x:
                pwd = os.getcwd()
                try:
                    os.chdir(os.path.dirname(fname))
                    load_model(db, x)
                finally:
                    os.chdir(pwd)
            elif 'ccmapi' in x:
                load_ccm_fixture(x)

        admin = User(
            sub=config.admin_sub,
            username=config.admin_username,
            email=config.admin_email,
            group=Group.default(),
            approved=True,
            is_superuser=True,
        )
        db.session.add(admin)
        db.session.commit()


def load_model(db, x):
    model = getattr(models, x['model'])
    tuple(map(lambda r: db.session.add(model(**r)), x['records']))


def load_ccm_fixture(x):
    if x['records'] is None:
        return

    access_token = get_access_token(config.aaa_api_token)
    tuple(map(partial(_get_or_create, api=x['ccmapi'],
                      access_token=access_token), x['records']))


def _get_or_create(r: 'record', api: 'str', access_token: 'str'):
    print('[{}] {}'.format(api, r['name']))
    if api == 'devicefeature':
        try:
            d = ag_ccmapi(access_token, "{}.get".format(api), {'key': r['name']})
            # update an existing device feature will not affect
            # any existing device model containing that feature
            # it will point to the old df parameter instead
            ag_ccmapi(access_token, "{}.update".format(api), {
                'df_id': d['df_id'],
                'df_name': r['name'],
                'type': r['type'],
                'parameter': r['parameter'],
                'comment': r['comment'],
            })
        except CCMAPIError:
            ag_ccmapi(access_token, "{}.create".format(api), {
                'df_name': r['name'],
                'type': r['type'],
                'parameter': r['parameter'],
                'comment': r['comment'],
            })
    elif api == 'devicemodel':
        try:
            ag_ccmapi(access_token, "{}.get".format(api), {'key': r['name']})

            # delete and recreate to update the device model
            try:
                ag_ccmapi(access_token, "{}.delete".format(api), {'dm': r['name']})
            except CCMAPIError:
                print("skip update device model {} because it is already in use !"
                      .format(r['name']))
                return

            ag_ccmapi(access_token, "{}.create".format(api), {
                'dm_name': r['name'],
                'dfs': [{'key': x['key']} for x in r['dfs']],
            })
        except CCMAPIError:
            ag_ccmapi(access_token, "{}.create".format(api), {
                'dm_name': r['name'],
                'dfs': [{'key': x['key']} for x in r['dfs']],
            })
    elif api == 'function':
        # If function name is exist, update the function code for login user only
        try:
            ag_ccmapi(access_token, "{}.create".format(api), {
                'fn_name': r['name'],
                'code': r['code'],
            })
        except CCMAPIError:
            pass


def ag_ccmapi(access_token, op, payload={}):
    '''
    :param op: The CCMAPI name which AutoGen support, e.g. 'account.login'
    :param payload: Data that should be provided to CCMAPI.
    :param access_token: access token
    :type op: string
    :type payload: dict.
    '''
    url = config.ag_url + '/ccm_api/'
    data = {
        "access_token": access_token,
        "api_name": op,
        "payload": payload
    }

    res = requests.post(url, json=data)
    if res.status_code != 200:
        raise CCMAPIError(res.text)

    return json.loads(res.text).get('result')


def get_access_token(api_token):
    client_id = config.client_id
    client_secret = config.client_secret
    OAUTH2_REDIRECT_URI = config.redirect_uri
    OIDC_AUTHORIZATION_ENDPOINT = config.authorization_endpoint
    OIDC_TOKEN_ENDPOINT = config.token_endpoint

    aaa_api_client.set_host(config.account_host)
    code = aaa_api_client.oauth2_authorize(api_token, OIDC_AUTHORIZATION_ENDPOINT,
                                           client_id, OAUTH2_REDIRECT_URI)
    token_response = aaa_api_client.oauth2_token_request(OIDC_TOKEN_ENDPOINT,
                                                         client_id, client_secret,
                                                         code, OAUTH2_REDIRECT_URI)
    access_token = token_response['access_token']
    return access_token


def main():
    parser = ArgumentParser(description='EduTalkcontroller')
    subparsers = parser.add_subparsers(help='available sub-commands')
    parser.add_argument(
        '-c', '--config',
        dest='ini_path',
        default=None,
        help='EduTalk ini config',
    )
    # subcommand: ``initdb``
    # TODO: configurable fixture path, but we do not need it ATM.
    initdb_parser = subparsers.add_parser('initdb', help='initialize database')
    initdb_parser.set_defaults(func=initdb)
    # subcommand: ``start``
    start_parser = subparsers.add_parser('start', help='start server')
    start_parser.set_defaults(func=start)
    # subcommand: ``genconf``
    genconf_parser = subparsers.add_parser(
        'genconf', help='generate sample ini file')
    genconf_parser.add_argument('dest', type=str, help='destination path')
    genconf_parser.set_defaults(func=genconf)

    args = parser.parse_args()
    loadini(args)

    if hasattr(args, 'func'):
        return args.func(args)
    parser.print_help()


def initdb(args):
    p = os.path.join(os.path.dirname(__file__), 'fixtures', 'default.yaml')
    return load_fixtures_and_create_admin(p)


def start(args):
    from edutalk.server import main as flask_main
    flask_main()


def loadini(args):
    config.read_config(args.ini_path)


def genconf(args):
    prefixes = [
        os.path.join(sys.prefix, 'share', 'edutalk'),
        os.path.join(os.path.dirname(__file__), '..', 'share'),
    ]
    for prefix in prefixes:
        src = os.path.join(prefix, 'edutalk.ini.sample')
        if os.path.isfile(src):
            break
    else:
        raise OSError('sample ini not found')

    dest = args.dest
    shutil.copy(src, dest)


if __name__ == '__main__':
    main()
