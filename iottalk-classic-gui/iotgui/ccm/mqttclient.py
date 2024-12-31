#!/usr/bin/env python3
"""
MQTT Module for IoTtalk2.

contains:
    __init__
    on_connect
    connect
    subscribe
    unsubscribe
    send_msg
    will_set
    loop_forever
"""
import atexit
import json
import logging
import os
import signal
import time

import paho.mqtt.client

from uuid import uuid4

from redis import StrictRedis

from iotgui import config, db
from iotgui.ccm.modules import CCMModule

log = logging.getLogger('mqttclient')
log.setLevel(logging.DEBUG)


class Client(CCMModule):
    """MQTT client for IoTtalk2."""

    # mqtt client id
    _client_id = None

    # mqtt client
    _client = None

    # redis client
    redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)

    def __init__(self):
        """Create a MQTT client and connect to IoTtalk2."""

    def _connect(self):
        self._client.connect(config.MQTT.host, port=config.MQTT.port)

    def _connect_with_retry(self, retry_times=5):
        error_msg = 'Fail to connect the MQTT broker'
        remain_retry_times = retry_times
        while True:
            try:
                remain_retry_times -= 1
                self._connect()
            except Exception:
                if remain_retry_times <= 0:
                    log.error('Fail to connect the MQTT broker')
                    os.kill(os.getpid(), signal.SIGINT)
                    break
                else:
                    if remain_retry_times == 1:
                        log.warning('{}, last retry after 3 seconds.'.format(error_msg))
                    else:
                        log.warning(
                            '{}, retry after 3 seconds, '
                            '{} times remained.'.format(error_msg, remain_retry_times))
                    time.sleep(3)
            else:
                break

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        for qos in granted_qos:
            # If the granted qos is not one of 0, 1 or 2, it means error
            if qos not in (0, 1, 2):
                log.error('Subscribe failed')
                '''
                Do not use sys.exit since the SystemExit will be trapped.
                Instead, send the SIGINT signal.
                See: https://tinyurl.com/lok266g
                '''
                os.kill(os.getpid(), signal.SIGINT)

    def on_connect(self, client, userdata, flags, rc):
        """Be executed when mqtt connected success."""
        # init database engine
        # don't put this in the __init__ stage to make pytest happy
        if rc != 0:
            log.error('Establish connection to MQTT broker failed')
            '''
            Do not use sys.exit since the SystemExit will be trapped.
            Instead, send the SIGINT signal.
            See: https://tinyurl.com/lok266g
            '''
            os.kill(os.getpid(), signal.SIGINT)

        log.info('Connect to MQTT broker successfully')
        db.connect()

        self._client.message_callback_add(config.MQTT.gui_req_topic.format('+'),
                                          self.receive_gui_msg)
        self._client.message_callback_add(config.MQTT.device_res_topic,
                                          self.receive_device_msg)
        self._client.message_callback_add(config.MQTT.graph_res_topic.format('+'),
                                          self.receive_graph_msg)
        self.subscribe(config.MQTT.gui_req_topic.format('+'))
        self.subscribe(config.MQTT.device_res_topic)

        # attach csm-device
        self.send_msg(config.MQTT.device_req_topic, {'op': 'attach'})

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            # Do not need to reconnect manually, paho will do it automatically.
            log.warning('Disconnected from the MQTT broker unexpectedly')
        else:
            log.info('mqtt disconnect')
            log.debug('rc: %s', rc)
            log.debug('userdata: %s', userdata)

    def connect(self):
        """Start connect to server."""
        self._client = paho.mqtt.client.Client(client_id=self.client_id)

        mqtt_scheme = str(config.MQTT.scheme).lower()

        # Enable TLS support if the MQTT scheme is mqtts.
        #
        # Ref: https://github.com/eclipse/paho.mqtt.python#tls_set
        if mqtt_scheme == 'mqtts':
            self._client.tls_set()

        if config.ENABLE_MQTT_AUTH:
            # Raise *RuntimeError* if MQTT auth function is enabled but plaintext
            # MQTT is used.
            if mqtt_scheme != 'mqtts':
                raise RuntimeError(
                    'Must use MQTT over TLS (mqtts) when MQTT auth function is enabled'
                )

            self._client.username_pw_set('ccm', config.AA_TOKEN)

        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_subscribe = self._on_subscribe
        # Set the retry interval
        self._client.reconnect_delay_set(min_delay=5, max_delay=30)
        # set detach csm-device will message
        self.will_set(config.MQTT.device_req_topic, {'op': 'detach'})
        log.info('connection to MQTT broker %s:%s', config.MQTT.host, config.MQTT.port)

        self._connect_with_retry()

    def subscribe(self, topic, qos=2):
        """
        Subscribe topic function.

        :param topic: The topic which want to subscribe.
        """
        if self._client:
            self._client.subscribe(topic, qos=qos)

    def unsubscribe(self, topic):
        """
        Unsubscribe topic function.

        :param topic: The topic which want to unsubscribe.
        """
        if self._client:
            self._client.unsubscribe(topic)

    def send_msg(self, topic, data, qos=2, retain=False):
        """
        Send mqtt message.

        :param topic: The topic which want to send.
        :param data: The payload which want to send.
        :param qos: optional, quality of message.
        :param retain: optional, retain the data.
        """
        return self._client.publish(topic, json.dumps(data), qos=qos, retain=retain)

    def will_set(self, topic, data, qos=2, retain=False):
        """
        Set will message.

        :param topic: The topic which want to set.
        :param data: The payload which want to set.
        :param qos: optional, quality of message.
        :param retain: optional, retain the data.
        """
        self._client.will_set(topic, json.dumps(data), qos=qos, retain=retain)

    def loop_forever(self):
        """Loop forever."""
        try:
            self._client.loop_forever()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            raise e
        finally:
            self.cleanup()

    def cleanup(self):
        # delete all simulator
        sim_do_ids = [do_id for do_id in self._simulator]
        for do_id in sim_do_ids:
            self.delete_simulator(None, do_id)

        # Send the detach message to the EC
        result = self.send_msg(config.MQTTConfig.device_req_topic, {'op': 'detach'})
        # Wait until the message is published
        result.wait_for_publish()
        self._client.disconnect()
        self._client.loop_stop()

    def loop_start(self):
        return self._client.loop_start()

    @property
    def client_id(self):
        if not self._client_id:
            self._client_id = 'ccm-{}'.format(uuid4())
        return self._client_id


# singleton
mqtt_module = Client()


def init():
    log.info('Initializing CCM module')
    global mqtt_module
    mqtt_module.connect()
    mqtt_module.loop_start()

    atexit.register(mqtt_module.cleanup)
    log.info('CCM server loop started')
