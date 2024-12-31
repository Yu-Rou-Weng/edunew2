import pytest


# TODO: launch a simulator for testing?
# TODO: duplication test:
#         1. given a device object
#         2. bind device A to it
#         3. without unbinding device A, bind device B to it.


@pytest.fixture
def dev_api(api_root, plan9, sample_dos):
    foo_id, bar_id = sample_dos
    foo_api = '{}/project/{}/deviceobject/{}/device/'.format(
        api_root, plan9, foo_id)
    bar_api = '{}/project/{}/deviceobject/{}/device/'.format(
        api_root, plan9, bar_id)
    return foo_api, bar_api


def test_list(http_client, dev_api):
    foo_api, bar_api = dev_api
    res = http_client.get(foo_api)
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    assert isinstance(res.json['data'], list)
    assert 'do_id' in res.json


def test_list_do_not_found(http_client, api_root, plan9):
    api = '{}/project/{}/deviceobject/42/device/'.format(api_root, plan9)
    res = http_client.get(api)
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_bind(http_client, dev_api):
    ...


def test_bind_not_found(api_root, plan9, sample_dos):
    ...


def test_unbind():
    ...


def test_unbind_not_found():
    ...
