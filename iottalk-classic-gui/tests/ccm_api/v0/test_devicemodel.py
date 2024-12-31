def test_list(http_client, sample_dms, api_root):
    res = http_client.get('{}/devicemodel/'.format(api_root))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    assert isinstance(res.json['data'], list)
    assert len(res.json['data']) == 2
    assert res.json['data'][0]['dm_id'] in sample_dms
    assert res.json['data'][1]['dm_id'] in sample_dms


def test_create_duplicate(http_client, sample_dms, api_root):
    # duplicate name
    res = http_client.put('{}/devicemodel/'.format(api_root), json={
        "dm_name": "FooModel",
        "df_list": [
            {
                "df_id": 12,
                "df_parameter": [{}]
            }
        ]
    })
    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'already exists' in res.json['reason']


def test_get(http_client, sample_dms, api_root):
    foo_id, bar_id = sample_dms
    res = http_client.get('{}/devicemodel/{}/'.format(api_root, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    assert 'dm_id' in data
    assert 'dm_name' in data
    assert 'dm_type' in data
    assert 'df_list' in data
    assert isinstance(data['df_list'], list)


def test_get_by_name(http_client, sample_dms, api_root):
    foo_id, bar_id = sample_dms
    res = http_client.get('{}/devicemodel/FooModel/'.format(api_root))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    assert res.json['data']['dm_id'] == foo_id


def test_get_not_found(http_client, sample_dms, api_root):
    res = http_client.get('{}/devicemodel/123/'.format(api_root))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_update(http_client, sample_dms, sample_dfs, api_root):
    foo_id, bar_id = sample_dms
    res = http_client.post('{}/devicemodel/{}/'.format(api_root, foo_id), json={
        'dm_name': 'FooModel',
        'df_list': [
            {
                'df_id': sample_dfs[0],
                'df_parameter': [{}],
            },
            {
                'df_id': sample_dfs[1],
                'df_parameter': [{}],
            }
        ]
    })
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'dm_id' in res.json
    assert res.json['dm_id'] == foo_id

    res = http_client.get('{}/devicemodel/{}/'.format(api_root, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert len(res.json['data']['df_list']) == 2


def test_update_df_list_empty(http_client, sample_dms, api_root):
    foo_id, bar_id = sample_dms
    res = http_client.post('{}/devicemodel/{}/'.format(api_root, foo_id), json={
        'dm_name': 'FooModel', 'df_list': []})
    assert res.status_code == 400
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'empty' in res.json['reason']


def test_delete(http_client, sample_dms, api_root):
    foo_id, bar_id = sample_dms
    res = http_client.delete('{}/devicemodel/{}/'.format(api_root, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'dm_id' in res.json
    assert res.json['dm_id'] == foo_id


def test_delete_not_found(http_client, sample_dms, api_root):
    foo_id, bar_id = sample_dms
    res = http_client.delete('{}/devicemodel/123/'.format(api_root))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']
