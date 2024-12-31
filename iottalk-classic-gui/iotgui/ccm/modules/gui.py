"""
GUI module.

contains:

    receive_gui_msg
    send_gui_msg
    gui_broadcast
"""
import json
import logging
import re
import traceback

from iotaa.client import Client as AAClient
from iotgui import config
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, Context, mqtt_server_thread
from iotgui.db import session_scope

log = logging.getLogger("{}GUI\033[0m".format(config.LOG_COLOR_GUI))
log.setLevel(config.LOG_LEVEL_GUI)


class GUI(Interface):
    """
    GUI class.

    Each GUI client use the difference <uuid> for topic like
        request: 'iottalk/api/gui/req/<uuid>'
        response:'iottalk/api/gui/res/<uuid>'

    Any client should send operation 'Attach' first.
    The <uuid> will be store in redis hashmap ('gui', <uuid>).
    """

    @mqtt_server_thread
    def receive_gui_msg(self, client, userdata, msg):
        """
        Receive GUI message.

        :param msg.poayload:
            {
                'op': <String> # API name,
                'data': <DICT> # data for API, check each API for detail.
                '_id': <UUID> # for client to map response and request
            }
        :return:
            {
                'op': <String> # API name,
                'state': Enum('ok', 'anno', 'error'),
                'msg': <String> # more information for state,
                'data': <DICT> # result of API called,
                '_id': <UUID> # for client to map response and request
            }
        """
        # log.debug("recv gui topic: {}".format(msg.topic))
        log.debug("recv gui payload: {}".format(msg.payload.decode()))

        uuid = self.uuid_from_topic(msg.topic)
        if uuid is None:
            log.warning("ignore invalid topic format `%s`", msg.topic)
            return

        payload = json.loads(msg.payload.decode())

        if 'op' not in payload:
            return

        if 'attach' == payload['op']:
            if not self.redis.hget('gui', uuid):
                self.redis.hset('gui', uuid, 1)
                payload['state'] = 'ok'
                self.send_gui_msg(uuid, payload)

        elif 'detach' == payload['op']:
            if self.redis.hget('gui', uuid):
                # Get the credential ID from the payload
                credential_id = payload.get('data', {}).get('credential_id')

                if config.ENABLE_MQTT_AUTH and credential_id:
                    aa_client = AAClient(config.AA_HOST, config.AA_PORT, 'ccm',
                                         config.AA_TOKEN)
                    try:
                        # Ask the AA subsystem to remove the corresponding credential
                        aa_client.delete_a_credential(credential_id)
                    except Exception:
                        ...

                self.redis.hdel('gui', uuid)
                payload['state'] = 'ok'
                self.send_gui_msg(uuid, payload)

        elif self.redis.hget('gui', uuid):
            if not payload or 'op' not in payload or '_id' not in payload:
                return

            u_id = self.redis.hget('user', payload['_id'])
            if not u_id:
                log.error('Authentication failed, user not found')
                payload['op'] = 'anno'
                payload['state'] = 'Authentication failed'
                payload['msg'] = 'Please login first.'
                self.send_gui_msg(uuid, payload)
                return

            try:
                data = payload.get('data', {})
                if data is None:
                    data = {}
                elif data.get('ctx'):
                    data.pop('ctx')

                with session_scope() as session:
                    ctx = Context(u_id.decode('utf-8'), session, uuid)
                    method = getattr(self, 'op_' + payload['op'])
                    result = method(ctx, **data)

                payload['state'] = 'ok'
                payload['data'] = result
                self.send_gui_msg(uuid, payload)
            except CCMError as e:
                log.error('session id: {}, user_id: {}, data: {}, error: {}'.format(
                    payload['_id'],
                    u_id,
                    data,
                    e.msg))

                payload['state'] = 'error'
                payload['msg'] = str(e.msg)
                self.send_gui_msg(uuid, payload)
            except Exception:
                err = traceback.format_exc()
                log.error(err)

                payload['state'] = 'error'
                payload['msg'] = err
                self.send_gui_msg(uuid, payload)

        else:
            log.error('Authentication Fail, Client UUID not find.')
            payload['op'] = 'anno'
            payload['state'] = 'Authentication Fail'
            payload['msg'] = 'Please attach first.'
            self.send_gui_msg(uuid, payload)

    def send_gui_msg(self, uuid, payload):
        """Send GUI message."""
        topic = config.MQTT.gui_res_topic.format(uuid)
        self.send_msg(topic, payload)

    def gui_broadcast(self, payload):
        """For announce to all gui client."""
        uuids = self.redis.hkeys('gui')
        for uuid in uuids:
            self.send_gui_msg(uuid.decode('utf-8'), payload)

    @staticmethod
    def uuid_from_topic(topic):
        """
        Extract client uuid from topic.
        Returns ``None`` if invalid.
        """
        m = re.search(r'\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$', topic)
        return m.group(0) if m else None
