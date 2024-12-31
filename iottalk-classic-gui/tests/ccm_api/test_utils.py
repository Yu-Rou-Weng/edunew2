from iotgui.ccm.api.utils import invalid_input


def test_invalid_input():
    data = {
        'foo': 42,
        'bar': 'baz',
        'qaz': [1, 2, 3],
        'qwe': {},
    }
    assert not invalid_input(data,
                             {'foo': int, 'bar': str, 'qaz': list, 'qwe': dict})

    # required not found
    assert invalid_input({}, {'x': 42})

    # str cannot be empty
    assert invalid_input({'foo': ''}, {'foo': str})
    # optional str field can be empty
    assert not invalid_input({'foo': ''}, {}, {'foo': str})

    # type invalid
    assert invalid_input({'foo': 'bar'}, {'foo': int})
    assert invalid_input({'foo': 42, 'bar': 'baz'}, {'foo': int}, {'bar': list})

    # optional keys
    assert not invalid_input({'foo': 'bar'}, {}, {'foo': str})
    assert not invalid_input({'foo': 42, 'bar': {}}, {'foo': int}, {'bar': dict})
    assert not invalid_input({'foo': 42}, {'foo': int}, {'bar': dict})

    # unknown keys
    assert invalid_input({'foo': 'bar'}, {}, {})

    # multiple type
    assert not invalid_input({'foo': None}, {'foo': (int, type(None))})
    assert not invalid_input({'foo': 42}, {'foo': (int, type(None))})
    assert invalid_input({'foo': 'bar'}, {'foo': (int, type(None))})
