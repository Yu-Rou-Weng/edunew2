import pytest


@pytest.fixture
def account(http_client, api_root):
    acc = {
        'username': 'test',
        'password': 'magic',
    }
    res = http_client.post('{}/account/create/'.format(api_root), json=acc)

    assert res.status_code == 200, res.json
    assert res.json['state'] == 'ok'
    assert 'id' in res.json

    yield acc


def test_create_duplicate(http_client, account, api_root):
    res = http_client.post('{}/account/create/'.format(api_root), json={
        'username': 'test',
        'password': 'magic2'})

    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json


def test_login(http_client, account, api_root):
    res = http_client.post('{}/account/login/'.format(api_root), json=account)

    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'id' in res.json


def test_login_failed(http_client, account, api_root):
    account['password'] = 'wtf'
    res = http_client.post('{}/account/login/'.format(api_root), json=account)

    assert res.status_code == 401
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
