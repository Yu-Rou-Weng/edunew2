'''
The internal-used data structure
'''
from iot.utils import SimpleLock


class Map(object):
    '''
    Dictionary

    The ``UserDict`` of python2 is not a new style object, so we do not
    inherit ``UserDict`` here; make an our own proxy class.

    >>> m = Map(foo='bar')
    >>> m
    {'foo': 'bar'}
    >>> m['foo'] = 42
    >>> m['foo']
    42
    '''

    def __init__(self, *args, **kwargs):
        self._data = dict(*args, **kwargs)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, value):
        return self._data.__getitem__(value)

    def __setitem__(self, key, value):
        return self._data.__setitem__(key, value)

    def __delitem__(self, key):
        return self._data.__delitem__(key)

    def __str__(self):
        return self._data.__str__()

    def __unicode__(self):
        return self._data.__unicode__()

    def __repr__(self):
        return self._data.__repr__()

    def __eq__(self, other):
        return self._data.__eq__(other)

    def __contains__(self, item):
        return self._data.__contains__(item)


class AtomMap(Map):
    '''
    The dictionary accepts only one-reader or one-writer at the sametime.

    >>> m = AtomMap(foo='bar')
    >>> m
    {'foo': 'bar'}
    >>> m['foo'] = 42
    >>> m['foo']
    42
    '''

    def __init__(self, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self._lock = SimpleLock()

    def __iter__(self):
        with self._lock:
            return super(type(self), self).__iter__()

    def __getitem__(self, value):
        with self._lock:
            return super(type(self), self).__getitem__(value)

    def __setitem__(self, key, value):
        with self._lock:
            return super(type(self), self).__setitem__(key, value)

    def __delitem__(self, key):
        with self._lock:
            return super(type(self), self).__delitem__(key)

    def __str__(self):
        return super(type(self), self).__str__()

    def __unicode__(self):
        return super(type(self), self).__unicode__()

    def __repr__(self):
        return super(type(self), self).__repr__()

    def __eq__(self, other):
        with self._lock:
            return super(type(self), self).__eq__(other)

    def __contains__(self, item):
        with self._lock:
            return super(type(self), self).__contains__(item)
