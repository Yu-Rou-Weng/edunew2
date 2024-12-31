import logging

from pony import orm as pony
from zope.event import classhandler as zevent

from iot import events
from iot.config import config
from iot.conn import iot_conn_mgr, DevAppState
from iot.csm.base import BaseAPIHandler

log = logging.getLogger('iottalk')


class Device(BaseAPIHandler):
    '''
    Device application api handler

    Spec is at ``csm.server.APIServer``.
    '''

    def __init__(self, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)

        self.attach()

        # register event handlers
        zevent.handler(events.DevAppRegister, self.anno)
        zevent.handler(events.DevAppOnline, self.anno)
        zevent.handler(events.DevAppDeregister, self.anno)
        zevent.handler(events.DevAppOffline, self.anno)

    def on_req(self, client, userdata, msg):
        payload = msg.payload

        log.debug('Device request: %r', payload)

        opcode = payload['op']
        if opcode == 'attach':
            self.attach()
        elif opcode == 'detach':
            self.detach()
        else:
            return self.unknown_op(payload, opcode)

    @property
    @pony.db_session()
    def snapshot(self):
        '''
        Get the initial snapshot of device applications state
        '''
        # copy ``conns`` here due to some race condition will change
        # the size of the dictionary. It causes ``RuntimeError``.
        conns = iot_conn_mgr.conns.copy()
        return {
            str(da.id): {
                **da.to_json(),
                'state': DevAppState.to_str(conns[da.id].ctrl.da_state)}
            for da in filter(
                None,
                (pony.get(res for res in config.db.Resource if res.id == uuid)
                 for uuid, _ in conns.items())
            )
        }

    def attach(self):
        '''
        This method should only be called once by ``self.__init__``.
        '''
        return self.res({
            'op': 'attach',
            'state': 'ok',
            'da_list': self.snapshot,
        })

    def anno(self, event):
        '''
        The announcement handler on device application.

        The ``iot_conn_mgr.conns.ctrl`` will emit a device application related
        event, then drive this handler.
        And those event will trigger a ``anno`` device broadcast.

        :param event.type: sould be (online|offline)
        '''
        log.debug('recieve event %s', event)

        '''
        There might be some race conditions between querying resource and
        deregister operation.
        '''
        try:
            da = event.res.to_json() if event.res else str(event.id)
        except Exception:
            log.warning('weird event: %s, no related Resource record in database',
                        event)
            return

        return self.res({
            'op': 'anno',
            'type': event.type,
            'timestamp': str(event.timestamp),
            'da': da
        })
