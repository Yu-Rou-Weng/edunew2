"""Python binding for CSM API."""
import requests

ENDPOINT = None
# ENDPOINT = 'http://localhost:9999'

# example
# profile = {
#     'd_name': 'D1',
#     'dm_name': 'MorSensor',
#     'u_name': 'yb',
#     'is_sim': False,
#     'df_list': ['Acceleration', 'Temperature'],
# }
# mac_addr = 'C860008BD249'
# csmapi.create(csmapi.mac_addr, csmapi.profile)
# create(mac_addr, profile)


def create(mac_addr, profile):
    r = requests.post(
        '{}/{}'.format(ENDPOINT, mac_addr),
        json={'profile': profile},
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return True


def delete(mac_addr):
    r = requests.delete('{}/{}'.format(ENDPOINT, mac_addr))
    if r.status_code != 200:
        raise Exception(r.text)

    return True


def push(mac_addr, df_name, data):
    r = requests.put(
        '{}/{}/{}'.format(ENDPOINT, mac_addr, df_name),
        json={'data': data},
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return True


def pull(mac_addr, df_name):
    r = requests.get('{}/{}/{}'.format(ENDPOINT, mac_addr, df_name))
    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()['samples']


def tree():
    r = requests.get('{}/tree'.format(ENDPOINT))
    if r.status_code != 200:
        raise Exception(r.text)
    return r.json()


# DF-module part #
# dfo_id == 0 means join
def dfm_push(na_id, dfo_id, stage, data):
    r = requests.put(
        '{}/dfm/{}/{}/{}'.format(ENDPOINT, na_id, dfo_id, stage),
        json={'data': data},
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return True


def dfm_pull(na_id, dfo_id, stage):
    r = requests.get(
        '{}/dfm/{}/{}/{}'.format(ENDPOINT, na_id, dfo_id, stage),
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()['samples']


def dfm_push_min_max(na_id, dfo_id, stage, min_max):
    r = requests.put(
        '{}/dfm/{}/{}/{}/min_max'.format(ENDPOINT, na_id, dfo_id, stage),
        json={'min_max': min_max},
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return True


def dfm_pull_min_max(na_id, dfo_id, stage):
    r = requests.get(
        '{}/dfm/{}/{}/{}/min_max'.format(ENDPOINT, na_id, dfo_id, stage),
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()['min_max']


def dfm_reset(na_id, dfo_id):
    r = requests.delete(
        '{}/dfm/{}/{}'.format(ENDPOINT, na_id, dfo_id),
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return True


def dfm_reset_all():
    r = requests.delete(
        '{}/dfm/'.format(ENDPOINT),
    )
    if r.status_code != 200:
        raise Exception(r.text)

    return True
