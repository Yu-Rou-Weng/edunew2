'''
Control message module

Handle the control plane
    - ``connect`` signal
    - ``disconnect`` signal
    - ``resume`` signal
    - ``suspend`` signal

A control message has following basic skeleton::

    {
        'msg_id': '...',
        'idf|odf': 'feature_name',
        'command': 'CMD',
        'topic': '...',
    }

And the expected response::

    {
        'msg_id': '...',
        'state': 'ok'
    }

Most of the control message is *device feature* level.
'''


def connect(*args, **kwargs):
    '''
    Info a device application to connect to a topic.

    The parameters refer to ``_publish_cmd``.
    '''
    return _publish_cmd('CONNECT', *args, **kwargs)


def disconnect(*args, **kwargs):
    '''
    Info a device application to disconnect from a topic.

    The parameters refer to ``_publish_cmd``.
    '''
    return _publish_cmd('DISCONNECT', *args, **kwargs)


def _publish_cmd(cmd, msg_id, mode, feature, topic, pub):
    '''
    :param msg_id: the message id client should return. It's useful for
                   distinguish response.
    :param mode: should be 'idf' or 'odf'
    :param feature: the feature name
    :param topic: the MQTT topic
    :param pub: the MQTT publish function
    '''
    return pub({
        'msg_id': msg_id,
        mode: feature,
        'command': cmd,
        'topic': topic,
    })


def resume():
    pass


def suspend():
    pass


def shutdown():
    pass
