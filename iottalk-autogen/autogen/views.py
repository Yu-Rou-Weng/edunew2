"""Django View for Autogen Subsystem."""
import pickle
import requests

from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import ccmapi.v0 as api

from ccmapi.exceptions import CCMAPIError

from .device import devicehandler
from .exceptions import JsonBadRequest
from .models import Device
from .utils import rgetattr, check_required, check_nonempty, check_type, invalid_input


def json_response(payload: dict = None) -> JsonResponse:
    payload = {} if payload is None else payload
    assert 'state' not in payload, 'duplicate key `state` in payload'
    payload.update({'state': 'ok'})
    return JsonResponse(payload)


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def create_device(request):
    """
    Create a new AutoGen device or update an existing device.

    :post.data code: The SA code for IoTtalk.
                     AutoGen will run this code as your device.
    :post.data version: Optional: 1 or 2, default: 2. This value is used to run
                        different iottalk dan libraries. Depends on the device
                        the user wants to create.

    :response token: The token of the device has been created.
                     Used to delete this device.
    """
    if request.method == 'OPTIONS':
        return HttpResponse('ok')

    payload = request.json
    payload.setdefault('version', 2)
    payload.setdefault('token', str(uuid4()))

    check_required(['code'], payload)
    check_nonempty(['code', 'token'], payload)
    check_type(int, ['version'], payload)

    dev = Device.objects.create(
        code=payload['code'],
        token=payload['token'],
        version=payload['version'])

    return json_response({
        'timestamp': datetime.now().timestamp(),
        'token': devicehandler.create_device(dev),
    })


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def delete_device(request):
    """
    Stop a existing AutoGen device.

    :post.data token: The token of the device to be stopped.
                      It is given by create API.
    """
    if request.method == 'OPTIONS':
        return HttpResponse('ok')

    payload = request.json
    check_required(['token'], payload)
    token = payload.get('token', None)
    dev = get_object_or_404(Device, token=token)
    token = devicehandler.delete_device(dev)
    dev.delete()
    return json_response({
        'timestamp': datetime.now().timestamp(),
        'token': token,
    })


@csrf_exempt
@require_http_methods(['POST', 'OPTIONS'])
def ccm_api(request):
    """
    CCM API.

    :post.data api_name: IoTtalk v1/v2 CCM API name.
    :post.data payload:  IoTtalk v1/v2 CCM API payload.
    :post.data username: Optional, IoTtalk v2 username.
    :post.data password: Optional, IoTtalk v2 password.
    :post.data access_token: Optional, IoTtalk account subsystem access token.
    """
    if request.method == 'OPTIONS':
        return HttpResponse('ok')

    payload = request.json

    if not payload:
        raise JsonBadRequest('Payload should be in JSON format.')

    payload_required = {'api_name': str, 'payload': dict}
    payload_optional = {'username': str, 'password': str, 'access_token': str}
    invalid_input(payload, payload_required, payload_optional)

    username = payload.get('username', None)
    password = payload.get('password', None)
    access_token = payload.get('access_token', None)
    api_name = payload.get('api_name')
    api_payload = payload.get('payload')

    if api_name not in settings.CCM_API_ARGS:
        raise JsonBadRequest(f'api_name {api_name} not found')

    api_args = settings.CCM_API_ARGS[api_name]
    invalid_input(
        api_payload,
        api_args.get('required', {}),
        api_args.get('optional', {})
    )

    try:
        # extract args from payload
        args = [api_payload.pop(k) for k in api_args.get('required', {}).keys()]

        # get api function from library ccmapi
        f = rgetattr(api, api_name)

        # login user for v2
        s = requests.Session()
        if 'ccm_cookie' in request.session:
            s.cookies.update(pickle.loads(bytes.fromhex(request.session['ccm_cookie'])))

        if username and password:
            u_id, cookie = api.account.login(username, password, session=s)
        elif access_token:
            u_id, cookie = api.account.oauth2(access_token, session=s)

        # TOFIX: Don't use pickle to store cookie
        request.session.update({'ccm_cookie': pickle.dumps(s.cookies).hex()})

        # assign logined session to invoke api
        api_payload.update({'session': s})

        result = f(*args, **api_payload)

    except AttributeError as e:
        raise JsonBadRequest(str(e))
    except KeyError as e:
        raise JsonBadRequest(f'{e} in the payload is required')
    except CCMAPIError as e:
        err = JsonBadRequest(e.msg)
        err.status = e.status_code
        raise err
    except requests.exceptions.ConnectionError:
        raise JsonBadRequest(
            'Connection error, please check that the IoTtalk Server ("api_url") '
            'can be connected normally.')
    except Exception as e:
        err = JsonBadRequest(str(e))
        print(e)
        raise err

    if api_name in ('account.login', 'account.oauth2'):
        return json_response({'result': {'u_id': result[0]}})

    return json_response({'result': result})
