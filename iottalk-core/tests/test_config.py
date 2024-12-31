import pytest

from six import string_types

from iot.config import config


def test_db_conf_schema():
    assert isinstance(config.db_conf['type'], string_types)
    assert isinstance(config.db_conf['url'], string_types)
    assert isinstance(config.db_conf['host'], string_types)
    assert isinstance(config.db_conf['port'], int)
    assert isinstance(config.db_conf['user'], string_types)
    assert isinstance(config.db_conf['passwd'], string_types)


def test_db_conf_invalid_key():
    with pytest.raises(ValueError):
        config.db_conf = {'answer': 42}


def test_db_conf_invalid_value():
    with pytest.raises(TypeError):
        config.db_conf = {'type': 42}


def test_db_conf_port_invalid_value():
    with pytest.raises(TypeError):
        config.db_conf = {'port': '42'}
