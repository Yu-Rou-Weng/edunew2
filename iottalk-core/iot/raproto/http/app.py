'''
Implementation of Resource Access Protocol HTTP API server.
'''
import logging

from uuid import uuid4

from pony import orm
from six import string_types
from tornado import ioloop, web
from tornado.web import url
from zope import event as zevent

from iot import events
from iot.config import config
from iot.conn import iot_conn_mgr
from iot.models import db_init
from iot.utils import suppress
from iot.utils.web import JSONHandler

UUID_PATTERN = r'[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}'

log = logging.getLogger('raproto-http')


class MQTTMixin(object):
    '''
    The MQTT helper mixin
    '''

    @property
    def mqtt_url(self):
        '''
        Get the mqtt url

        :return: a ``dict`` with following schema::

            {
                'scheme': 'mqtt',
                'host': 'example.org',
                'port': 1883,
                'ws_scheme': 'ws',
                'ws_port': 1884,
            }

            Note the ``ws_*`` is for the web application connecting via
            MQTT over Websocket.

        .. todo::
            Search the best mqtt server for device
        '''
        ws = {
            'ws_{}'.format(k): v
            for k, v in config.ws_conf.items() if k != 'host'
        }
        conf = config.mqtt_conf
        conf.update(ws)
        return conf

    @staticmethod
    def mqtt_ctrl_chans(uuid):
        '''
        Get the MQTT control channel info

        :param uuid: the ``UUID`` object

        >>> id_ = 'a54b5bf9-c39b-4248-b611-80d1ed4a36df'
        >>> chan = MQTTMixin.mqtt_ctrl_chans(id_)
        >>> assert chan == [
        ...     'a54b5bf9-c39b-4248-b611-80d1ed4a36df/ctrl/i',
        ...     'a54b5bf9-c39b-4248-b611-80d1ed4a36df/ctrl/o'
        ... ]
        '''
        base = '{}/ctrl'.format(str(uuid))
        return ['{}/i'.format(base), '{}/o'.format(base)]


class RAProtoHandler(JSONHandler, MQTTMixin):
    '''
    Resource Access Protocol Handler
    '''

    @orm.db_session
    def get(self, uuid):
        res = config.db.Resource.get(id=uuid)
        if res is None:
            self.send_error(404, msg='id not found')

        payload = res.to_json()
        payload['state'] = 'ok'
        self.write(payload)

    def put(self, uuid):
        '''
        In case of device application re-registered without deregistration
        (``DELETE``) first, it is considered as a long-runing device
        application.

        To prevent from the race condition of HTTP requests,
        we generate a new ``revision`` token for every PUT request.
        '''
        log.debug('Recieve UUID: %r', uuid)
        response = {
            'id': uuid,
            'state': 'ok',
        }

        try:
            self.verify_put_data(self.json)
        except AssertionError as e:
            self.send_error(403, msg=e.args[0])
            return

        try:
            with orm.db_session(serializable=True):
                resource = config.db.Resource.get_for_update(id=uuid)
                if resource is None:
                    if self.json.get('name') is None:
                        # auto-generated device name
                        self.json['name'] = self.generate_device_name(self.json)

                    resource = config.db.Resource(id=uuid, **self.json)
                else:
                    # case of device application re-registered
                    log.info('Device application re-registered: %r', uuid)
                    resource.revision = uuid4()
        except ValueError as e:  # usually raise from Resource's py_check
            self.send_error(403, msg=e.args[0])
            return
        except OverflowError as e:  # from ``generate_device_name``
            self.send_error(510, msg=e.args[0])
            return

        rev = response['rev'] = str(resource.revision)
        response['name'] = resource.name

        # TODO: check available server
        # but now we simply pick up first ``accept_protos``
        if resource.accept_protos[0].lower() == 'mqtt':
            response['url'] = self.mqtt_url
            response['ctrl_chans'] = self.mqtt_ctrl_chans(resource.id)
            sub_topic, pub_topic = response['ctrl_chans']
            iot_conn_mgr.mqtt_ctrl(resource.id, pub_topic, sub_topic, rev)

        self.write(response)

    def post(self, uuid):
        pass

    @orm.db_session(serializable=True)
    def delete(self, uuid):
        res = config.db.Resource.get_for_update(id=uuid)
        if res is None:
            self.send_error(404, msg='id not found')
            return
        elif str(res.revision) != self.json.get('rev'):
            # check revision to prevent race condiction
            self.send_error(400, msg='revision out-of-date or unknown')
            return

        payload = {
            'id': uuid,
            'state': 'ok',
        }
        res.delete()
        zevent.notify(events.DevAppDeregister(uuid))
        self.write(payload)

    def verify_put_data(self, d):
        '''
        verify the data from ``put``.
        The schema follow the `spec
        <http://iottalk-spec.rtfd.io/en/latest/api/res_access/http.html#put-id>`_.

        :type d: dict
        '''
        assert isinstance(d.get('accept_protos', None), list), (
            "Field 'accept_protos' is required and should be a list")
        assert d['accept_protos'], "Field 'accept_protos' can not be empty"

        name = d.get('name', None)
        if name is not None:
            assert isinstance(name, string_types), (
                "Field 'name' should be a string")

        for field in ('idf_list', 'odf_list'):
            val = d.get(field, None)
            if val is not None:
                assert isinstance(val, list), (
                    'Field {!r} should be a list'.format(field))
                assert val, '{!r} can not be empty'.format(field)

        profile = d.get('profile', None)
        assert isinstance(profile, dict), (
            "Field 'profile' is required and it should be a json object")
        assert 'model' in profile, "Field 'profile.model' is required."

        aval_fields = ('name', 'accept_protos', 'idf_list', 'odf_list',
                       'profile')
        for key in d.keys():
            assert key in aval_fields, 'Unknown field: {!r}'.format(key)

    def generate_device_name(self, d):
        '''
        try to generate and assign a name to a device

        :param d: a ``Dict`` of the request payload
        :return: the generated name
        '''
        for i in range(100):
            name = '{0:02d}'.format(i)
            if 'profile' in d and 'model' in d['profile']:
                # leverage the info from the optional `profile` field
                name = '{}.{}'.format(name, d['profile']['model'])

            if config.db.Resource.exists(name=name) is False:
                return name

        # I'm abusing this exception.
        # If we need more type of exception in future,
        # please create a new class for this.
        raise OverflowError('Name pool is full')


def mkapp():
    db_init()
    return web.Application(
        (
            url(r'/({})'.format(UUID_PATTERN), RAProtoHandler, name='index'),
        ),
        debug=config.debug
    )


def main():
    app = mkapp()
    app.listen(config.http_port, address=config.bind)

    log.info('Start raproto http server on %s', config.http_port)
    with suppress(KeyboardInterrupt):
        ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
