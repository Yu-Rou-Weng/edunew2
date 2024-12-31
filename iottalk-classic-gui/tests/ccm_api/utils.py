import threading
import json
import uuid

from queue import Queue

import paho.mqtt.client as mqtt


def mkref():
    return str(uuid.uuid4())


def block_sub(topic):
    """
    Setup a MQTT connection and block until the subscription is ready.
    """
    def on_connect(client, userdata, flags, rc):
        client.subscribe(topic)
        userdata['sema'].release()

    def on_subscribe(client, userdata, mid, qos):
        userdata['sema'].release()

    def on_message(client, userdata, msg):
        print('on_message', msg.payload)  # for debugging
        mq = userdata['mq']
        mq.put(msg.payload)

    sema = threading.Semaphore()
    sema.acquire()

    userdata = {
        'sema': sema,
        'mq': Queue()
    }
    mqtt_client = mqtt.Client(userdata=userdata)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_subscribe = on_subscribe
    mqtt_client.on_message = on_message
    mqtt_client.connect('localhost')
    mqtt_client.loop_start()

    sema.acquire()  # wait for on_connect
    sema.acquire()  # wait for on_subscribe

    return mqtt_client, userdata


def sub_wait(userdata, timeout=1):
    """
    wait single message from MQTT channel
    """
    mq = userdata['mq']
    msg = mq.get(timeout=timeout)
    return json.loads(msg.decode())
