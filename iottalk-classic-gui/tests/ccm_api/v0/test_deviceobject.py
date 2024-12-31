import pytest


@pytest.mark.xfail(strict=True)
def test_create_invalid_df(http_client, api_root, plan9, sample_dms,
                           sample_dfs):
    res = http_client.put('{}/project/{}/deviceobject/'.format(api_root, plan9),
                          json={'dm_id': foo_dm, 'df': sample_dfs})  # noqa: F821
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'invalid Device Feature' in res.json['reason']


@pytest.mark.xfail(strict=True)
def test_create_dm_not_found(http_client, api_root, plan9, sample_dms,
                             sample_dfs):
    res = http_client.put('{}/project/{}/deviceobject/'.format(api_root, plan9),
                          json={'dm_id': 100, 'df': sample_dfs})
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']
    assert 'Device Model' in res.json['reason']


def test_create_df_not_found(http_client, api_root, plan9, sample_dms,
                             sample_dfs):
    foo_dm, _ = sample_dms
    res = http_client.put('{}/project/{}/deviceobject/'.format(api_root, plan9),
                          json={'dm_id': foo_dm, 'df': [42, 43, 44]})
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']
    assert 'Device Feature' in res.json['reason']


def test_get(http_client, api_root, plan9, sample_dms, sample_dfs, sample_dos):
    foo_id, bar_id = sample_dos
    res = http_client.get('{}/project/{}/deviceobject/{}/'.format(
        api_root, plan9, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    data = res.json['data']
    assert 'do' in data
    assert data['do']['do_id'] == foo_id
    assert data['do']['dfo'] == ['foo', 'bar']
    assert data['dm_id'] == sample_dms[0]
    assert data['dm_name'] == 'FooModel'

    res = http_client.get('{}/project/{}/deviceobject/{}/'.format(
        api_root, plan9, bar_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json
    data = res.json['data']
    assert 'do' in data
    assert data['do']['do_id'] == bar_id
    assert data['do']['dfo'] == ['foo', 'bar']
    assert data['dm_id'] == sample_dms[1]
    assert data['dm_name'] == 'BarModel'


def test_get_not_found(http_client, api_root, plan9, sample_dos):
    res = http_client.get('{}/project/{}/deviceobject/42/'.format(
        api_root, plan9))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_delete(http_client, api_root, plan9, sample_dos):
    foo_id, bar_id = sample_dos
    res = http_client.delete('{}/project/{}/deviceobject/{}/'.format(
        api_root, plan9, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'do_id' in res.json
    assert res.json['do_id'] == foo_id


def test_delete_return_404(http_client, api_root, plan9, sample_dos):
    res = http_client.delete('{}/project/{}/deviceobject/42/'.format(
        api_root, plan9))
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']


def test_update(http_client, api_root, plan9, sample_dos, sample_dfs):
    foo_id, _ = sample_dos
    res = http_client.post(
        '{}/project/{}/deviceobject/{}/'.format(api_root, plan9, foo_id),
        json={'df': [sample_dfs[1]]})
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'do_id' in res.json
    assert res.json['do_id'] == foo_id

    res = http_client.get('{}/project/{}/deviceobject/{}/'.format(
                          api_root, plan9, foo_id))
    assert res.status_code == 200
    assert res.json['state'] == 'ok'
    assert 'data' in res.json

    data = res.json['data']
    assert 'do' in data
    assert 'dfo' in data['do']
    assert len(data['do']['dfo']) == 1


def test_update_invalid_df(http_client, api_root, plan9, sample_dos, sample_dfs):
    foo_id, _ = sample_dos
    res = http_client.post(
        '{}/project/{}/deviceobject/{}/'.format(api_root, plan9, foo_id),
        json={'df': [42]})
    assert res.status_code == 404
    assert res.json['state'] == 'error'
    assert 'reason' in res.json
    assert 'not found' in res.json['reason']
