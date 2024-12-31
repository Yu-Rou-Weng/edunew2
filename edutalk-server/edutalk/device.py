from contextlib import suppress
from time import sleep

from flask import jsonify
from flask_login import current_user

from edutalk.models import LectureProject
from edutalk.utils import ag_ccmapi
from edutalk.exceptions import CCMAPIError


def graceful_bind(x: LectureProject, do_id, d_id, max_retry=5):
    with suppress(CCMAPIError):
        ag_ccmapi(current_user.id, 'device.unbind',
                  {'p_id': x.p_id, 'do_id': do_id})  # unbind first

    ag_ccmapi(current_user.id, 'device.get', {'p_id': x.p_id, 'do_id': do_id})

    for _ in range(max_retry):
        try:
            ag_ccmapi(current_user.id, 'device.bind',
                      {'p_id': x.p_id, 'do_id': do_id, 'd_id': d_id})
            return jsonify({'state': 'ok'}), 200
        except CCMAPIError:
            # mac_addr not found might be caused by race condition
            sleep(1)
            continue

    return jsonify({'state': 'error'}), 400


def unbind(x: LectureProject, do_id):
    ag_ccmapi(current_user.id, 'device.unbind', {'p_id': x.p_id, 'do_id': do_id})
    return jsonify({'state': 'ok'})
