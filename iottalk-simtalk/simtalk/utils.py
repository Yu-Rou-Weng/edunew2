import json
import re
import requests
import logging

from uuid import uuid4

from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.shortcuts import redirect
from django.template import loader

from .color import SimTalkColor
from .models import AccessToken, Project, User

log = logging.getLogger(SimTalkColor.wrap(SimTalkColor.logger, 'SIMTALK.utils'))
log.setLevel(level=logging.INFO)

# Create Oauth2 client for general use
oauth2_client = OAuth()
oauth2_client.register(
    name='iottalk',
    client_id=settings.OAUTH2_CLIENT_ID,
    client_secret=settings.OAUTH2_CLIENT_SECRET,
    server_metadata_url=settings.OIDC_DISCOVERY_ENDPOINT,
    client_kwargs={'scope': 'openid', }
)


def ccmapi(op, payload, u_id):
    '''
    :param op: The CCMAPI name which AutoGen support, e.g. 'account.login'
    :param payload: Data that should be provided to CCMAPI.
    :param u_id: Owner ID of iottalk data.
    :type op: string
    :type payload: dict.
    :type u_id: int
    '''
    # Check User and it's username and password
    user = User.objects.filter(u_id=u_id).first()
    if not user:
        raise Exception(f"User not find, u_id: {u_id}")

    url = settings.AG_API_URL + 'ccm_api/'
    data = {
        "api_name": op,
        "payload": payload
    }

    # Authentication
    if not settings.OAUTH2_CLIENT_ID:
        data.update({
            "username": user.username,
            "password": user.password,
        })
    else:
        accesstoken_record = (
            AccessToken.objects.filter(user_id=u_id).latest("id")
        )
        data.update({
            "access_token": accesstoken_record.token,
        })

    res = requests.post(url, json=data)
    if res.status_code // 100 != 2:
        raise Exception(res.text)

    return json.loads(res.text).get('result')


def test_ag_oauth2(access_token):
    '''
    Check access token is valid and has user data in CCM.

    If valid, return u_id.
    Otherwise, return None.
    '''
    url = settings.AG_API_URL + 'ccm_api/'
    data = {
        "api_name": "account.oauth2",
        "payload": {"access_token": access_token}
    }
    res = requests.post(url, json=data)
    if res.status_code // 100 != 2:
        log.error('AG oauth2 failed.')
        log.debug(res.text)
        return

    return json.loads(res.text).get('result').get('u_id')


def test_ag_login(username, password):
    '''
    Check username and password is valid in CCM.

    If valid, return u_id.
    Otherwise, return None.
    '''

    url = settings.AG_API_URL + 'ccm_api/'
    data = {
        "api_name": 'account.login',
        "payload": {'username': username, 'password': password}
    }
    res = requests.post(url, json=data)
    if res.status_code // 100 != 2:
        log.error('AG login failed: %s', username)
        log.debug(res.text)
        return

    return json.loads(res.text).get('result').get('u_id')


def start_simulator(do_record):
    log.info('Start AG Device: do_id: %s', do_record.do_id)

    # Fetch all related information
    do_info = do_record.to_dict()

    # Prepare DF function name, which use '_' instead of '-'
    for dfo in do_info['dfo_list']:
        dfo['df_func_name'] = dfo['df_name'].replace('-', '_')

    # Get the AG sa device template
    template = loader.get_template('sa/sa.py')

    # Render the DO information to the template
    code = template.render({
        'api_url': settings.CSM_API_URL,
        'dm_name': do_record.dm_name,
        'mac_addr': str(uuid4()),
        'do_id': do_record.do_id,
        'dfo_list': do_info['dfo_list'],
    })

    log.debug(code)

    # Send AG API to create simulator
    url = settings.AG_API_URL + 'create_device/'
    res = requests.post(url, json={'code': code, 'version': settings.AG_DEVICE_VERSION})

    # If failed
    if res.status_code // 100 != 2:
        log.error('AG create_device failed.')
        raise Exception('AG create_device failed.')

    log.debug('AG create_device result: %s', res.text)

    # Update the DeviceObject.ag_token
    ag_token = json.loads(res.text).get('token')
    log.info('AG create_device successful: ag_token: %s', ag_token)

    return ag_token


def stop_simulator(do_record):
    log.info('Stop AG Device: do_id: %s, ag_token: %s',
             do_record.do_id,
             do_record.ag_token)

    # First, Send AG request to delete AG device
    url = settings.AG_API_URL + 'delete_device/'
    res = requests.post(url, json={'token': do_record.ag_token})

    # Something wrong
    if res.status_code // 100 != 2:
        log.error('AG delete_device Failed: %s', res.text)
        raise Exception('AG delete_device failed.')

    log.debug('AG delete_device result: %s', res.text)

    # Second, Stop successful, update DO record
    do_record.ag_token = ''
    do_record.save()

    return True


def update_ccm_simulation(p_id, u_id, sim):
    log.info('Change the simulation: p_id: %s, sim: %s', p_id, sim)

    # Send AG ccm_api to set project sim to 'on'
    res = ccmapi('simulation.' + sim, {'p_id': p_id}, u_id)
    log.debug('ccm_api.simulation.%s: %s', sim, res)

    # Update Project record
    Project.objects.filter(p_id=p_id).update(sim=res)

    return sim == res


def security_redirect(next_url):
    if next_url and type(next_url) is str and \
            re.search(settings.REDIRECT_REGEX, next_url, re.IGNORECASE):

        return redirect(next_url)

    return redirect('/')
