import base64
import json

from urllib.parse import quote

import requests


host = 'http://127.0.0.1:8000'  # hostname:port, without tailing '/'


def set_host(url: str):
    global host
    if url.endswith('/'):  # remove tailing '/'
        url = url[0:-1]
    host = url
    pass


class InvalidLoginException(Exception):
    pass


class InvalidTokenException(Exception):
    pass


class PermissionException(Exception):
    pass


class InvalidRequestException(Exception):
    pass


class ServerException(Exception):
    pass


def obtain_api_token(username: str, password: str):
    url = host + "/accounts/api/obtain_api_token"
    headers = {'content-type': 'application/json'}
    payload = {
        "username": username,
        "password": password
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    if r.status_code == 200:
        res = json.loads(r.content)
        return res["token"]
    elif r.status_code == 400:
        raise InvalidLoginException("invalid username or password !")
    else:
        raise Exception(r.text)
    pass


def create_temp_user(api_token: str, username: str, password: str, expire_in: int or str):
    """
    create a temp user, will be deleted after specified expire_in duration
    :param api_token:
    :param username: username you want to use
    :param password: password you want to use
    :param expire_in: num of seconds or 'never'
    :return: id of created user
    """
    # note that the server is checking and deleting the expired user
    # in fixed time interval (ex. 5 min) so the expire_in may not accurate
    # the expire_in is at least 300 sec and at most 90 days,
    # the server will also check this
    expire_in = int(max(expire_in, 300)) if expire_in != 'never' else 'never'

    url = host + "/accounts/api/create_temp_user"
    headers = {'content-type': 'application/json',
               "Authorization": "Token {}".format(api_token)}
    payload = {
        "username": username,
        "password": password,
        "expire_in": expire_in
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    if r.status_code == 200:
        res = json.loads(r.content)
        print("temp User '{}' id='{}' has been created successfully !"
              .format(username, res['user_id']))
        return res['user_id']
    elif r.status_code == 401:
        raise InvalidTokenException(r.text)
    elif r.status_code == 403:
        raise PermissionException(r.text)
    elif r.status_code == 400:
        raise InvalidRequestException(r.text)
    elif r.status_code == 500:
        raise ServerException(r.text)
    else:
        raise Exception(r.text)
    pass


def create_user(api_token: str, username: str, email: str, password: str, is_staff=False):
    """
    create a user
    :param api_token:
    :param username: username you want to use
    :param email: email you want to use
    :param password: password you want to use
    :param is_staff: create a user in Staff group or not
    :return: id of created user
    """
    url = host + "/accounts/api/create_user"
    headers = {'content-type': 'application/json',
               "Authorization": "Token {}".format(api_token)}
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "is_staff": is_staff,
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    if r.status_code == 200:
        res = json.loads(r.content)
        print("User '{}' id='{}' has been created successfully !"
              .format(username, res['user_id']))
        return res['user_id']
    elif r.status_code == 401:
        raise InvalidTokenException(r.text)
    elif r.status_code == 403:
        raise PermissionException(r.text)
    elif r.status_code == 400:
        raise InvalidRequestException(r.text)
    elif r.status_code == 500:
        raise ServerException(r.text)
    else:
        raise Exception(r.text)
    pass


def reset_user_password(api_token: str, user_id: int or str, password: str):
    """
    reset the password of a target user
    :param api_token:
    :param user_id: target id (or 'sub'  field in x-talk) of user
    :param password: new password of target user
    """
    url = host + "/accounts/api/reset_user_password"
    headers = {'content-type': 'application/json',
               "Authorization": "Token {}".format(api_token)}
    payload = {
        "user_id": user_id,
        "password": password,
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    if r.status_code == 200:
        print("the password of temp User id='{}' has been reset successfully !"
              .format(user_id))
    elif r.status_code == 401:
        raise InvalidTokenException(r.text)
    elif r.status_code == 403:
        raise PermissionException(r.text)
    elif r.status_code == 400:
        raise InvalidRequestException(r.text)
    elif r.status_code == 500:
        raise ServerException(r.text)
    else:
        raise Exception(r.text)
    pass


def oauth2_authorize(api_token: str, authorize_uri, client_id: str, redirect_uri):
    url = "{}?response_type=code&client_id={}&scope=openid&redirect_uri={}"\
        .format(authorize_uri, client_id, quote(redirect_uri))
    headers = {"Authorization": "Token {}".format(api_token)}
    r = requests.post(url, headers=headers)
    if r.status_code == 200:
        res = json.loads(r.content)
        return res['code']
    elif r.status_code == 401:
        raise InvalidTokenException(r.text)
    elif r.status_code == 403:
        raise PermissionException(r.text)
    elif r.status_code == 400:
        raise InvalidRequestException(r.text)
    elif r.status_code == 500:
        raise ServerException(r.text)
    else:
        raise Exception(r.text)
    pass


def oauth2_token_request(token_uri, client_id: str, client_secret: str, code: str,
                         redirect_uri):
    url = token_uri
    credential = "{}:{}".format(quote(client_id), quote(client_secret))
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
               "Authorization": b"Basic {}" + base64.b64encode(credential.encode("utf-8"))}
    data = 'grant_type=authorization_code&code={}&redirect_uri={}'\
        .format(code, quote(redirect_uri))
    r = requests.post(url, headers=headers, data=data)
    if r.status_code == 200:
        res = json.loads(r.content)
        return res
    elif r.status_code == 401:
        raise InvalidTokenException(r.text)
    elif r.status_code == 403:
        raise PermissionException(r.text)
    elif r.status_code == 400:
        raise InvalidRequestException(r.text)
    elif r.status_code == 500:
        raise ServerException(r.text)
    else:
        raise Exception(r.text)
    pass
