import pytest

from pony import orm as pony

from iot import models


def test_check_accept_protos_invalid():
    with pytest.raises(ValueError):
        models.check_accept_protos(["answer", "42"])

    with pytest.raises(ValueError):
        models.check_accept_protos(["mqtt", "42"])


def test_check_accept_protos_invalid_type():
    assert models.check_accept_protos({'magic': 42}) is False


@pony.db_session
@pytest.mark.parametrize('param, ans', [
    ({}, {}),
    ({'idf_list': []}, {}),
    ({'idf_list': [], 'odf_list': []}, {}),
    ({'idf_list': [42], 'odf_list': []}, {'idf_list': [42]}),

    ({'idf_list': [42], 'odf_list': [24]},
     {'idf_list': [42], 'odf_list': [24]}),

    ({'idf_list': [], 'odf_list': [], 'name': 'magic'}, {'name': 'magic'}),

    ({'idf_list': [], 'odf_list': [], 'name': 'magic', 'profile': {}},
     {'name': 'magic'}),

    ({'name': 'magic', 'profile': {'model': 'BetaCat'}},
     {'name': 'magic', 'profile': {'model': 'BetaCat'}}),

    ({'name': '', 'profile': {'model': 'BetaCat'}},
     {'profile': {'model': 'BetaCat'}}),
])
def test_Resource_to_json(param, ans, db, uuid, new_uuid):
    rev = str(new_uuid)
    res = db.Resource(id=uuid, revision=rev, **param)
    ans.update(dict(id=uuid, rev=rev))

    res_json = res.to_json()
    assert isinstance(res_json.pop('register_time'), float)
    assert res_json == ans
