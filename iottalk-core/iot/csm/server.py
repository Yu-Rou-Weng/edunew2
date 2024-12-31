'''
Communication SubModule (CSM)

This module implements an API server. This server has following capibility:

    - Deliver the control message.

    - High-privilege API, usually used by GUI front-end.
      This server will wait for requests on ``iottalk/api/req/+``,
      and responses on ``iottalk/api/res/+``.

'''
import logging

from functools import partial

from iotutils.mqtt import JsonClient, mqtt_json_payload

from iot.config import config
from iot.csm.device import Device
from iot.csm.graph import Graph
from iot.utils import suppress

log = logging.getLogger('iottalk.csm')

# workaround for strange RuntimeError from logger, seems there are some race
# conditions in log printing.
logging.raiseExceptions = False


class APIServer(object):
    '''
    For the request topic, we use the pattern
    ``iottalk/api/req/<client-id>/...``.
    Each request topic has a corresponding *response* topic.

    The available api calls:
        - graph api
        - device api


    Global API
    ----------------------------------------------------------------------
    The ``detach`` opcode is also on:

    - ``iottalk/api/req/<client-id>`` - for detaching all services


    Graph API
    ----------------------------------------------------------------------

    The topic of graph api call should be
    ``iottalk/api/req/<client-id>/graph/<graph-id>``.

    The ``detach`` opcode is also available on:

    - ``iottalk/api/req/<client-id>/graph`` - for detaching all graphs
    - ``iottalk/api/req/client_id`` - for detaching all services

    The graph operation has following json format::

        {
            'op': 'operation',
            'other_op_param': 'value',
        }

    The available operation code:
        - ``attach``
        - ``detach``
        - ``add_funcs``
        - ``rm_funcs``
        - ``add_link``
        - ``rm_link``
        - ``set_join``: setup or changing the join function
        - ``set_df_func``: changing the idf/odf function
        - ``start_monitor``
        - ``stop_monitor``

    ``attach`` and ``detach`` request is for graph creating and destroying::

        {
            'op': 'attach|detach'
        }

    .. note::
        Please mark the ``detach`` as last will and testamnet,
        in order to prevent memory leak. If we do not ``detach`` properly,
        the instance of ``iot.csm.graph.Graph`` will not be GC.

    ``attach`` and ``detach`` response::

        {
            'op': 'attach|detach',
            'state': 'ok',
        }

    ``add_funcs`` request::

        {
            'op': 'add_funcs',
            'codes': [
                'def f(): ...',
                'def g(): ...'
            ],
            'digests': [
                'SHA256 of f',
                'SHA256 of g'
            ],
        }

    ``add_funcs`` response::

        {
            'op': 'add_funcs',
            'state': 'ok',
            'digests': [
                'SHA256 of f',
                'SHA256 of g'
            ],
        }

    ``rm_funcs`` request::

        {
            'op': 'rm_funcs',
            'digests': [
                '...',
            ],
        }

    ``add_link`` and ``rm_link`` request::

        {
            'op': 'add_link|rm_link',
            'da_id': 'uuid',
            'idf|odf': 'feature_name',
            'input_type': 'sample|variant',  // optional field for ``add_link``
                                             // it only applied in case of idf
                                             // treat input data as a sample or variant
            'func': 'digest',  // optional field for ``add_link``
            'depends': {  // optional for ``add_link``
                'name of f': 'SHA256 of f',
                'name of g': 'SHA256 of g',
            },
            'param_no': n,  // optional field for ``add_link``
                            // data length is adjusted to this number
            'tag_param_no': n,  // optional field for ``add_link``
                                // tag data length is adjusted to this number
        }

    ``add_link`` and ``rm_link`` response::

        {
            'op': 'add_link|rm_link',
            'da_id': 'uuid',
            'idf|odf': 'feature_name',
            'input_type': 'sample|variant',  // optional field for 'idf' of ``add_link``
            'func': 'digest',  // optional field for ``add_link``
            'depends': {  // optional for ``add_link``
                'name of f': 'SHA256 of f',
                'name of g': 'SHA256 of g',
            },
            'param_no': n,  // optional field for ``add_link``
            'tag_param_no': n,  // optional field for ``add_link``
            'state': 'ok',
        }

    ``set_join`` request::

        {
            'op': 'set_join',
            'prev': 'function digest',  //``None`` (``null`` in json) for first setup
            'new': 'new': 'function digest',  //None (null in json) for disable join function  # noqa: E501
            'depends': {  // optional
                'name of f': 'SHA256 of f',
                'name of g': 'SHA256 of g',
            },
        }

    ``set_join`` response::

        {
            'op': set_join',
            'state': 'ok',
            'new': 'function digest',
            'depends': {  // optional
                'name of f': 'SHA256 of f',
                'name of g': 'SHA256 of g',
            },
        }

    ``set_df_func`` request::

        {
            'op': 'set_df_func',
            'da_id': 'uuid',
            'idf|odf': 'feature_name',
            'input_type': 'sample|variant',  // optional field for 'idf' of ``add_link``
            'prev': 'function digest',  //``None`` (``null`` in json) for first setup
            'new': 'function digest',
            'depends': {  // optional
                'name of f': 'SHA256 of f',
                'name of g': 'SHA256 of g',
            },
        }

    ``set_df_func`` response::

        {
            'op': 'set_df_func',
            'da_id': 'uuid',
            'idf|odf': 'feature_name',
            'state': 'ok',
            'new': 'function digest',
            'depends': {  // optional
                'name of f': 'SHA256 of f',
                'name of g': 'SHA256 of g',
            },
        }

    The error response has following general format::

        {
            'op': 'opcode',
            'state': 'error',
            'reason': 'error_reason',
            'other_payload': '...',
        }


    Device API
    ----------------------------------------------------------------------

    The topic of graph api call should be
    ``iottalk/api/req/<client-id>/device``.

    This api endpoint provide notification about device applications.

    The available operation code:

    - ``attach``
    - ``detach``
    - ``anno`` for announcement


    ``attach``
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    Initialize this service and get the init state of device applications.

    And the following device application state changes will be revealed on this
    channel.

    Request::

        {
            'op': 'attach',
        }

    If attach success, we will got following response.
    If more than one attach request arrive, we will ignore the lagger.

    ::

        {
            'op': 'attach',
            'state': 'ok',
            'da_list': {
                'id': {
                    'name': ...,
                    'id': ...,
                    'idf_list': ...,
                    'odf_list': ...,
                },
            },
        }


    ``detach``
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    .. note::
        Please mark this ``detach`` as last will and testamnet,
        in order to prevent memory leak. If we do not ``detach`` properly,
        the instance of ``iot.csm.device.Device`` will not be GC.

    Request::

        {
            'op': 'detach',
        }

    Response::

        {
            'op': 'detach',
            'state': 'ok',
        }


    ``anno``
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    Client will recieve announcement on the response channel if there is any
    D.A. state changes.

    There are some types of announcement message:

        - ``online``

        - ``changed``

        - ``offline``

    Type ``online``::

        {
            'op': 'anno',
            'timestamp': '...',
            'type': 'online',
            'da': {
                ...  // new and whole state
            }
        }

    Type ``changed``::

        {
            'op': 'anno',
            'timestamp': '...',
            'type': 'changed',
            'da': {
                ...  // changed field(s)
            }
        }

    Type ``offline``::

        {
            'op': 'anno',
            'timestamp': '...',
            'type': 'offline',
            'da': 'da_id',
        }

    The field ``timestamp`` will be a time-based uuid.

    '''

    def __init__(self):
        self.topic_prefix = 'iottalk/api'
        self.client = JsonClient(client_id='csm-{}'.format(config.session_id))
        if config.enable_mqtt_auth:  # Set username and password when MQTT auth is enabled
            self.client.username_pw_set('ec', config.aaa_token)
        self.client.on_connect = self._on_connect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_json_message = self.msg_dispatcher
        self.client.reconnect_delay_set(min_delay=5, max_delay=30)
        self.client.connect(config.mqtt_conf['host'],
                            port=config.mqtt_conf['port'])
        self.gapi_client = {}  # graph api client
        self.dapi_client = {}  # device api client

        log.info('server session id %s', config.session_id)

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            '''
            If the return code is not 0, it means connection error.
            Make the EC crash immediately.
            '''
            raise SystemExit('Establish connection to MQTT server failed')

        # Subscribe the device related topic
        self.client.subscribe('{}/req/+/device'.format(self.topic_prefix), qos=2)
        # Subscribe the graph related topic
        self.client.subscribe('{}/req/+/graph/+'.format(self.topic_prefix), qos=2)
        log.debug('api server connected')

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            log.warning('Disconnected from the MQTT broker unexpectedly')

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        for qos in granted_qos:
            if qos not in (0, 1, 2):
                '''
                If the granted qos is not one of 0, 1 or 2, it means error.
                Make the EC crash immediately.
                '''
                raise SystemExit('Subscribe failed')

    def loop_forever(self):
        with suppress(KeyboardInterrupt):
            self.client.loop_forever()

    def msg_add_callback(self, topic):
        '''
        Get a helper function for add/remove on_message callback

        Available function attribute:

        :f.client: the mqtt client instance
        :f.callback: the set callback function
        :f.topic: the mqtt topic
        :f.remove_callback: function for remove callback
        '''
        def f(callback):
            if f.callback is not None:
                raise RuntimeError(
                    'message callback for {!r} already set'.format(f.topic))

            f.callback = mqtt_json_payload(callback, raise_error=False)
            f.client.message_callback_add(f.topic, f.callback)
            return f.callback

        f.topic = topic
        f.client = self.client
        f.callback = None
        f.remove_callback = partial(self.client.message_callback_remove,
                                    f.topic)
        return f

    def msg_dispatcher(self, client, userdata, msg):
        log.debug('on api server message: \n%r:\n%r', msg.topic, msg.payload)

        topic = msg.topic.split('/')[3:]

        if len(topic) == 1:
            client_id, api_type = topic[0], 'service'
        elif 2 <= len(topic) <= 3:
            client_id, api_type = topic[:2]
        else:
            log.warning('Invalid topic %r', topic)
            return

        if api_type == 'service':  # accept the detach message
            if msg.payload.get('op') == 'detach':
                return self.detach_all(client_id)

        elif api_type == 'graph':
            if len(topic) == 3:
                graph_id = topic[2]
                return self.attach_graph_api(client_id, graph_id, msg)

            # maybe a detach message
            if msg.payload.get('op') == 'detach':
                return self.detach_graph_api(client_id)

        elif api_type == 'device':
            return self.attach_dev_api(client_id, msg)

        else:
            log.warning('Unknown api type: %r', api_type)
            return

    def graph_res_topic(self, client_id, graph_id=None):
        '''
        The response topic of graph api service

        :param client_id: <clien-id> in the topic
        :param graph_id: <graph-id> in the topic
        '''
        return '{}/res/{}/graph/{}'.format(
            self.topic_prefix, client_id, graph_id if graph_id else '')

    def graph_req_topic(self, client_id, graph_id=None):
        '''
        The request topic of graph api service

        :param client_id: <clien-id> in the topic
        :param graph_id: <graph-id> in the topic
        '''
        return '{}/req/{}/graph/{}'.format(
            self.topic_prefix, client_id, graph_id if graph_id else '')

    def attach_graph_api(self, client_id, graph_id, msg):
        '''
        Attach to initiate ``iot.csm.graph.Graph``

        :param client_id: <clien-id> in the topic
        :param graph_id: <graph-id> in the topic
        :param msg: the mqtt msg object
        '''
        res_topic = self.graph_res_topic(client_id, graph_id)
        publish = partial(self.client.publish_json, res_topic, qos=2)

        if client_id not in self.gapi_client:
            log.info('New client connected: %s', client_id)
            # init a empty dict for storing graph map
            # FIXME: potential race condition when creating gapi_client
            self.gapi_client[client_id] = {}

        api_client = self.gapi_client[client_id]
        # FIXME: if the graph_id in api_client, imply that the Graph in woring.
        #        and maybe no message will be heard here
        if graph_id not in api_client:
            # check attach info
            opcode = msg.payload.get('op')
            if opcode != 'attach':
                reason = 'Unknown graph id {}'.format(graph_id)
                log.warning(reason)
                msg.payload['state'] = 'error'
                msg.payload['reason'] = reason
                publish(msg.payload)
                return

            log.info('New graph added: %s', graph_id)
            # init a new graph object
            api_client[graph_id] = Graph(
                req=self.msg_add_callback(msg.topic),
                res=publish,
                res_topic=res_topic,
                req_topic=self.graph_req_topic(client_id, graph_id),
                id_=graph_id,
                pub_func=partial(self.client.publish_json, qos=2),
                destroy_cb=self.detach_graph_api_cb(client_id, graph_id))

            msg.payload['state'] = 'ok'
            publish(msg.payload)

    def detach_graph_api_cb(self, client_id, graph_id):
        '''
        The function factory of detach callback for graph api

        :param client_id: <clien-id> in the topic
        :param graph_id: <graph-id> in the topic
        '''
        def cb():
            del self.gapi_client[client_id][graph_id]

        return cb

    def detach_graph_api(self, client_id):
        '''
        Handle the last will and testamnet of graph api connection.

        If we got detach msg on ``iottalk/api/<client-id>/graph``,
        delete all the graphs related to this client.
        '''
        log.info('Destroy whole graph api services on client %r', client_id)

        for graph in tuple(self.gapi_client[client_id].values()):
            graph.detach()

        self.gapi_client[client_id].clear()
        del self.gapi_client[client_id]

        topic = self.graph_res_topic(client_id)
        self.client.publish_json(topic, {'op': 'detach', 'state': 'ok'}, qos=2)

    def attach_dev_api(self, client_id, msg):
        '''
        :param client_id: <client-id> part in the topic
        :param msg: the mqtt msg object
        '''
        if self.dapi_client.get(client_id) is not None:
            log.warning('The device api service is not working on %r ?',
                        client_id)
            return

        res_topic = 'iottalk/api/res/{}/device'.format(client_id)
        publish = partial(self.client.publish_json, res_topic, qos=2)

        log.info('New device api service for %r', client_id)

        self.dapi_client[client_id] = Device(
            req=self.msg_add_callback(msg.topic),
            res=publish,
            res_topic=res_topic,
            destroy_cb=self.detach_dev_api_cb(client_id))

    def detach_dev_api_cb(self, client_id):
        '''
        The function factory of detach callback for device api

        :param client_id: <client-id> part in the topic
        '''
        def cb():
            del self.dapi_client[client_id]

        return cb

    def detach_all(self, client_id):
        '''
        Detach all the api services.
        '''
        if client_id in self.gapi_client:
            self.detach_graph_api(client_id)

        if client_id in self.dapi_client:
            self.dapi_client[client_id].detach()


def main():
    log.info('start CSM API server')
    server = APIServer()
    server.loop_forever()
