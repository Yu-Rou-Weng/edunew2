def test_list(http_client, api_root, plan9, sample_nas):
    res = http_client.get('{}/project/{}/na/'.format(api_root, plan9))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    assert len(data) == len(sample_nas)


def test_list_pid_not_found(http_client, api_root, plan9, sample_nas):
    res = http_client.get('{}/project/42/na/'.format(api_root))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_info(http_client, api_root, plan9, sample_nas):
    foo_na, bar_na = sample_nas
    res = http_client.get('{}/project/{}/na/{}/'.format(
        api_root, plan9, foo_na))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    assert data['na_id'] == foo_na
    assert data['na_name'] == 'JoinFoo'
    assert 'input' in data
    assert 'output' in data
    assert 'multiple' in data


def test_info_not_found(http_client, api_root, plan9, sample_nas):
    # TODO: project id not found
    # TODO: na id not found
    ...


def test_delete(http_client, api_root, plan9, sample_nas):
    foo_na, bar_na = sample_nas
    res = http_client.delete('{}/project/{}/na/{}/'.format(
        api_root, plan9, foo_na))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert res.json['na_id'] == foo_na

    res = http_client.get('{}/project/{}/na/'.format(api_root, plan9))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    assert len(data) == len(sample_nas) - 1


def test_delete_not_found(http_client, api_root, sample_nas):
    # TODO: na_id not found
    ...
