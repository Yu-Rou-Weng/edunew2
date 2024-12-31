"""Utils for Autogen Subsystem."""
import functools

from .exceptions import JsonBadRequest


def get_client_ip(request):
    """
    Retrive client IP address from request.

    This function will retrive from HTTP_X_FORWARDED_FOR first,
    then REMOTE_ADDR.

    :param request: The Django request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))


def _check(keys, payload, pred, msg):
    for k in keys:
        if not pred(k, payload):
            raise JsonBadRequest(msg.format(k=k))


def _required(k, payload):
    return k in payload


def _nonempty(k, payload):
    return len(payload.get(k, [])) != 0


def check_required(keys: list, payload: dict):
    return _check(keys, payload, _required, 'field `{k}` not found')


def check_nonempty(keys: list, payload: dict):
    return _check(keys, payload, _nonempty, 'field `{k}` should not be empty')


def check_type(typ: type, keys: list, payload: dict):
    return _check(keys, payload, lambda x, d: isinstance(d[x], typ),
                  'field `{k}` type error')


def invalid_input(x: dict, required: dict, optional: dict = {}):
    '''
    Check the required field in the given json input,
    If invalid, raise the error message.
    If valid, returns nothing.

    :param dict: a dictionary comes from requests.json
    :param required: a dictionary contains the required field and its type::

        {
            'field1': str,
            'field2': int,
            'field3': (int, type(None)),  // tuple only, list is not allowed
            ...
        }

    :param optional: the optional field
    '''
    if x is None:
        raise JsonBadRequest('Content-type should be `application/json` and '
                             'body should not be empty')

    # field existence
    _check(required, x, _required, 'field `{k}` is required')

    # check unknown keys
    keyset = set(required.keys()).union(optional.keys())
    _check(x, keyset, _required, 'field `{k}` unknown')

    # check type
    for y in (required, optional):
        for k, types in y.items():
            if k not in x:
                continue

            types = types if isinstance(types, tuple) else (types,)
            for typ in types:
                if isinstance(x[k], typ):
                    break
            else:
                raise JsonBadRequest(f'field `{k}` should be type `{typ}`')

    # check str non-empty
    for k, v in x.items():
        if k not in required:  # skip check for optional fields
            continue
        if isinstance(v, str) and not v:
            raise JsonBadRequest(f'field `{k}` should not be empty')

    return  # ok
