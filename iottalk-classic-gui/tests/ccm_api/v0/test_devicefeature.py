def test_list(http_client, sample_dfs, api_root):
    res = http_client.get('{}/devicefeature/'.format(api_root))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'

    assert 'input' in res.json
    assert isinstance(res.json['input'], list)
    assert len(res.json['input']) == 1

    assert 'output' in res.json
    assert isinstance(res.json['output'], list)
    assert len(res.json['output']) == 1


def test_create_duplicate(http_client, sample_dfs, api_root):
    # df_name already exists
    res = http_client.put('{}/devicefeature/'.format(api_root), json={
        'df_type': 'output',
        'df_name': 'foo',
        'df_parameter': [{}],
    })
    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'already exists' in res.json['reason']


def test_create_param_empty(http_client, sample_dfs, api_root):
    # df_parameter is empty
    res = http_client.put('{}/devicefeature/'.format(api_root), json={
        'df_type': 'input',
        'df_name': 'baz',
        'df_parameter': [],
    })
    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'df_parameter' in res.json['reason']


def test_create_type_invalid(http_client, sample_dfs, api_root):
    # df_type invalid
    res = http_client.put('{}/devicefeature/'.format(api_root), json={
        'df_type': 'magic',
        'df_name': 'baz',
        'df_parameter': [{}],
    })
    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'feature type' in res.json['reason']


def test_get(http_client, sample_dfs, api_root):
    foo_id, bar_id = sample_dfs
    res = http_client.get('{}/devicefeature/{}/'.format(api_root, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    assert res.json['data']['df_name'] == 'foo'


def test_get_by_name(http_client, sample_dfs, api_root):
    foo_id, bar_id = sample_dfs
    res = http_client.get('{}/devicefeature/foo/'.format(api_root))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    assert res.json['data']['df_id'] == foo_id


def test_get_not_found(http_client, sample_dfs, api_root):
    res = http_client.get('{}/devicefeature/42/'.format(api_root))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_update(http_client, sample_dfs, api_root):
    foo_id, bar_id = sample_dfs
    res = http_client.post('{}/devicefeature/{}/'.format(api_root, foo_id),
                           json={
                               'df_name': 'foo',
                               'df_type': 'output',
                               'df_parameter': [{}]}
                           )
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert res.json['df_id'] == foo_id

    # check fields
    res = http_client.get('{}/devicefeature/{}/'.format(api_root, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    assert res.json['data']['df_name'] == 'foo'
    assert res.json['data']['df_type'] == 'output'
    assert len(res.json['data']['df_parameter']) == 1


def test_update_not_found(http_client, sample_dfs, api_root):
    res = http_client.post('{}/devicefeature/123/'.format(api_root),
                           json={
                               'df_name': 'foo',
                               'df_type': 'output',
                               'df_parameter': [{}]}
                           )
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_delete(http_client, sample_dfs, api_root):
    foo_id, bar_id = sample_dfs
    res = http_client.delete('{}/devicefeature/{}/'.format(api_root, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'df_id' in res.json
    assert res.json['df_id'] == foo_id

    res = http_client.get('{}/devicefeature/'.format(api_root))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert len(res.json['input']) == 0
    assert len(res.json['output']) == 1


def test_delete_not_found(http_client, sample_dfs, api_root):
    res = http_client.delete('{}/devicefeature/123/'.format(api_root))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']
