def test_duplicated(http_client, plan9, api_root):
    res = http_client.put('{}/project/'.format(api_root), json={
        "p_name": "plan9",
    })

    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json


def test_list(http_client, plan9, api_root):
    res = http_client.get('{}/project/'.format(api_root))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    assert len(res.json['data']) == 1

    res = http_client.put('{}/project/'.format(api_root), json={
        "p_name": "plan42",
    })
    assert res.status_code == 201

    res = http_client.get('{}/project/'.format(api_root))
    assert len(res.json['data']) == 2


def test_delete(http_client, plan9, api_root):
    res = http_client.delete('{}/project/{}/'.format(api_root, plan9))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'

    res = http_client.delete('{}/project/{}/'.format(api_root, plan9))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json


def test_info(http_client, plan9, api_root):
    res = http_client.get('{}/project/{}/'.format(api_root, plan9))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    assert data['p_id'] == plan9
    assert data['p_name'] == 'plan9'


def test_not_found(http_client, account, api_root):
    res = http_client.get('{}/project/42/'.format(api_root))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_update(http_client, plan9, api_root):
    res = http_client.post('{}/project/{}/'.format(api_root, plan9), json={
        'status': 'on',
    })
    assert res.status_code == 200, res.json
    assert res.json['state'] == 'ok'
    assert res.json['p_id'] == plan9
    assert res.json['status'] == 'on'
