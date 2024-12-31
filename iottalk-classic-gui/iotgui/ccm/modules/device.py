"""
Device Module.

contains:

    receive_device_msg
    register_device
    deregister_device
    broken_device # TODO: function name

    op_get_device_list
    op_bind_device
    op_unbind_device
"""
import datetime
import json
import logging

from sqlalchemy import and_, or_

from iotgui import config
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser, Context, mqtt_server_thread
from iotgui.db import model, session_scope

log = logging.getLogger("{}DEVICE\033[0m".format(config.LOG_COLOR_DEVICE))
log.setLevel(config.LOG_LEVEL_DEVICE)


class Device(Interface):
    """Device class."""

    _devices = {}

    @mqtt_server_thread
    def receive_device_msg(self, client, userdata, msg):
        """Receive device msg from CSM."""
        # log.debug("recv device topic: {}".format(msg.topic))
        log.debug("recv device payload: {}".format(msg.payload.decode()))

        payload = json.loads(msg.payload.decode())

        if 'op' not in payload:
            return

        if 'attach' == payload['op']:
            with session_scope() as session:
                # attach graph
                na_records = session.query(model.NetworkApplication).all()
                for na_record in na_records:
                    # attach esm-graph
                    self.attach_graph(Context(None, session), na_record.na_id)
                    # set detach esm-graph will message
                    self.will_set(config.MQTT.graph_req_topic.format(na_record.na_id), None)

                # create simulator
                project_records = (session.query(model.Project)
                                          .filter(model.Project.sim == 'on')
                                          .all())
                for project_record in project_records:
                    # for server restart without any user, but need set user config
                    ctx = Context(project_record.u_id, db_session=session)
                    self.op_turn_on_simulation(ctx, project_record.p_id)

                # get devices in db
                device_records = (session.query(model.Device).all())
                db_device_list = {device.mac_addr: device.d_id for device in device_records}

                # add device
                for id_ in payload['da_list']:
                    self.register_device(Context(None, session),
                                         payload['da_list'][id_])
                    if id_ in db_device_list:
                        db_device_list.pop(id_)

                # delete not exist device in db
                for mac_addr in db_device_list:
                    (session.query(model.DeviceObject)
                            .filter(model.DeviceObject.d_id == db_device_list[mac_addr])
                            .update({'d_id': None}))
                    (session.query(model.Device)
                            .filter(model.Device.mac_addr == mac_addr)
                            .delete())
                    session.commit()

        elif 'anno' == payload['op']:
            if 'register' == payload['type']:
                # add device to db
                with session_scope() as session:
                    self.register_device(Context(None, session),
                                         payload['da'])
            elif payload['type'] in ('online', 'offline'):
                with session_scope() as session:
                    self.change_device_state(Context(None, session),
                                             payload['da'], payload['type'])
            elif 'deregister' == payload['type']:
                # remove device from db
                with session_scope() as session:
                    self.deregister_device(Context(None, session),
                                           payload['da'])
        elif 'detach' == payload['op']:
            # Nothing todo
            return
        else:
            pass

    def register_device(self, ctx, device):
        """
        Register new Device.

        :param device:
            {
                'id': id, # mapping to mac_addr of csm device
                'name': d_name,
                'state': online/offline,  # device state
                'register_time': unix timestamp,  # device register time to CCM
                'profile': {
                    'dm_name': '<DeviceModel.dm_name>'
                    'u_name': u_name, # optional for user
                    'is_sim': True / False,  # optional for simulator
                    'do_id': do_id,  # optional for simulator
                }
            }

        :return:
            '<Device.d_id>'
        """
        mac_addr = device['id']
        dm_name = device['profile'].get('model')
        status = device.get('state', 'offline')  # if given by anno, or, by register
        is_sim = device['profile'].get('is_sim', False)
        extra_setup_webpage = device['profile'].get('extra_setup_webpage', '')
        device_webpage = device['profile'].get('device_webpage', '')
        register_time = device.get('register_time', datetime.datetime.now())

        db_session = ctx.db_session

        # parsing ``register_time``
        if isinstance(register_time, float):
            register_time = datetime.datetime.fromtimestamp(register_time)

        # for server restart without any user, but need set user config
        if device['profile'].get('u_name'):
            user_record = (db_session
                           .query(model.User)
                           .filter(model.User.u_name == device['profile']['u_name'])
                           .first())
            if user_record:
                ctx.u_id = user_record.u_id

        # check mac_addr existed
        device_record = (db_session
                         .query(model.Device)
                         .filter(model.Device.mac_addr == mac_addr)
                         .first())
        if device_record:
            device['d_id'] = device_record.d_id
            self._devices[device['id']] = device
            (db_session
             .query(model.Device)
             .filter(model.Device.d_id == device['d_id'])
             .update({'status': 'online'}))
            db_session.commit()
            # TODO: maybe update device info ?
            return True

        # check DeviceModel existed
        dm_record = (db_session
                     .query(model.DeviceModel)
                     .filter(model.DeviceModel.dm_name == dm_name)
                     .first())
        if not dm_record:
            return False

        # Add Device
        new_device = model.Device(
            d_name=device['name'],
            dm_id=dm_record.dm_id,
            mac_addr=mac_addr,
            is_sim=is_sim,
            u_id=ctx.u_id,
            register_time=register_time,
            status=status,  # FIXME: I want to rename it as ``state``
            extra_setup_webpage=extra_setup_webpage,
            device_webpage=device_webpage,
        )
        db_session.add(new_device)
        db_session.commit()

        # save device info to cache
        device['d_id'] = new_device.d_id
        self._devices[device['id']] = device

        # simulator
        if is_sim and 'do_id' in device['profile']:
            do_id = device['profile']['do_id']
            self.op_bind_device(ctx, do_id, new_device.d_id, False)

            if str(do_id) in self._simulator:
                self._simulator[str(do_id)].d_id = new_device.d_id

        return True

    def deregister_device(self, ctx, uuid):
        """
        Deregister Device.

        :param uuid:
            device uuid

        :return:
            device uuid
        """
        db_session = ctx.db_session
        device_record = (db_session.query(model.Device)
                                   .filter(model.Device.mac_addr == uuid)
                                   .first())
        if device_record:
            d_id = device_record.d_id

            # Unmount all DeviceObject
            do_records = (db_session.query(model.DeviceObject)
                                    .filter(model.DeviceObject.d_id == d_id)
                                    .all())

            for do_record in do_records:
                self.op_unbind_device(ctx, do_record.do_id)

            # delete device
            (db_session.query(model.Device)
                       .filter(model.Device.d_id == d_id)
                       .delete())
            db_session.commit()

            # announce all gui client
            self.gui_broadcast({'op': 'anno',
                                'type': 'deregister',
                                'data': {'d_id': d_id}})

        if uuid in self._devices:
            del self._devices[uuid]

        return uuid

    def change_device_state(self, ctx, uuid, state):
        """
        Change device state.

        :param uuid: device uuid
        :param state: device state (online|offline)

        :return:       device uuid
        """
        db_session = ctx.db_session
        # update device
        (db_session.query(model.Device)
                   .filter(model.Device.mac_addr == uuid)
                   .update({'status': state}))
        db_session.commit()

        # announce all gui client
        if uuid in self._devices:
            self.gui_broadcast({'op': 'anno',
                                'type': state,
                                'data': self._devices[uuid]})
        return uuid

    def op_get_device_list(self, ctx, do_id):
        """
        Get all online Devices.

        If DeviceObject only contains the input DeviceFeture,
        return all of devices include other user's.

        If DeviceObject contains the output DeviceFeature,
        return the devices which is public or user owned.

        :param do_id: <DeviceObject.do_id>
        :type do_id: int

        :return:
            {
                'do_id': <DeviceObject.do_id>,
                'device_list': [ <Device>, ...]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        if not self.is_device_object_exist(ctx, do_id):
            raise CCMError('Device Object id {} not found'.format(do_id))

        # get DeviceModel by DeviceObject
        do_record = (db_session.query(model.DeviceObject)
                               .filter(model.DeviceObject.do_id == do_id)
                               .first())
        dm_id = do_record.dm_id

        # check that is only contains sensor odf
        # Issue: only allow bind other user's device for idf (by YB)
        dfo_records = (db_session.query(model.DFObject)
                                 .select_from(model.DeviceObject)
                                 .join(model.DFObject)
                                 .join(model.DeviceFeature)
                                 .filter(model.DeviceObject.do_id == do_id,
                                         model.DeviceFeature.df_type == 'output')
                                 .all())

        # Query all Device by DeviceModel
        if dfo_records:
            # output device
            # conditions:
            # 1. match DeviceModel
            # 2. not simulator
            # 3. not usage (single bind) - by YB
            # 4. out of claimed time or claimed by login user
            time_filter = ()
            if config.OWNERSHIP_TIMEOUT:
                time_filter = (datetime.datetime.now()
                               - datetime.timedelta(0, config.OWNERSHIP_TIMEOUT))
                time_filter = (model.Device.register_time < time_filter,)
            single_bind = ()  # support output device single bind (by YB)
            if config.ODF_SINGLE_BIND:
                single_bind = (model.DeviceObject.d_id.is_(None),)
            query = (
                db_session.query(model.Device)
                          .outerjoin(model.DeviceObject,
                                     # support output device single bind (by YB)
                                     model.Device.d_id == model.DeviceObject.d_id)
                          .filter(model.Device.dm_id == dm_id,
                                  model.Device.is_sim == 0,
                                  or_(model.Device.u_id == u_id,
                                      and_(model.Device.u_id.is_(None),
                                           *time_filter)),
                                  *single_bind)
                          .order_by(model.Device.d_id)
                          .all())
        else:
            # input device
            # allow all device be use with conditions:
            # 1. match DeviceModel
            # 2. not simulator
            # 3. out of claimed time or claimed by any user
            filter_ = (model.Device.u_id.is_(None), model.Device.u_id == u_id)
            if config.OWNERSHIP_TIMEOUT:
                filter_ = (datetime.datetime.now()
                           - datetime.timedelta(0, config.OWNERSHIP_TIMEOUT))
                filter_ = (model.Device.u_id.isnot(None),
                           model.Device.register_time < filter_)
            query = (db_session.query(model.Device)
                               .filter(model.Device.dm_id == dm_id,
                                       model.Device.is_sim == 0,
                                       or_(*filter_))
                               .order_by(model.Device.d_id)
                               .all())

        result = {
            'do_id': do_id,
            'device_list': []
        }
        for device in query:
            result['device_list'].append(record_parser(device))

        return result

    def op_bind_device(self, ctx, do_id, d_id, check_sim=True):
        """
        Bind the Device to the Device Object.

        Server will check the Network Application,
        and automatically execute the data path.

        :param do_id: '<DeviceObject.do_id>'
        :param d_id: '<Device.d_id>'
        :param check_sim: auto unbind simulator or not
        :type do_id: int
        :type d_id: int
        :type check_sim: boolean

        :return:
            {
                'd_name': <Device.d_name>
            }
        """
        db_session = ctx.db_session

        # check Device
        device_record = (db_session.query(model.Device)
                                   .filter(model.Device.d_id == d_id)
                                   .first())
        if not device_record:
            raise CCMError('Device id {} not found'.format(d_id))

        # unbind simulator
        if check_sim:
            if str(do_id) in self._simulator:
                self.op_unbind_device(ctx, do_id, check_sim=False)

        # bind the device
        (db_session.query(model.DeviceObject)
                   .filter(model.DeviceObject.do_id == do_id,
                           or_(model.DeviceObject.d_id == 0,
                               model.DeviceObject.d_id.is_(None)))
                   .update({'d_id': d_id}))
        db_session.commit()

        # add esm graph link
        na_records = (db_session.query(model.DF_Module.na_id,
                                       model.DF_Module.dfo_id)
                                .select_from(model.DeviceObject)
                                .join(model.DFObject)
                                .join(model.DF_Module)
                                .filter(model.DeviceObject.do_id == do_id,
                                        model.DeviceObject.d_id == d_id)
                                .group_by(model.DF_Module.na_id,
                                          model.DF_Module.dfo_id)
                                .all())
        for na_id, dfo_id in na_records:
            self.add_link(ctx, na_id, dfo_id)

        return {'d_name': device_record.d_name}

    def op_unbind_device(self, ctx, do_id, check_sim=True):
        """
        Unbind the Device to the Device Object.

        :param do_id: <DeviceObject.do_id>
        :param check_sim: auto bind simulator or not
        :type do_id: int
        :type check_sim: boolean

        :return:
            {
                'do_id': '<DeviceObject.do_id>'
            }
        """
        db_session = ctx.db_session

        # check device
        do_record = (db_session.query(model.DeviceObject)
                               .select_from(model.DeviceObject)
                               .filter(model.DeviceObject.do_id == do_id)
                               .first())
        if do_record and do_record.d_id:
            # remove esm graph link.
            device_record = (db_session.query(model.Device)
                                       .filter(model.Device.d_id == do_record.d_id)
                                       .first())
            if device_record:  # if can't find device, maybe race condition
                mac_addr = device_record.mac_addr
                na_records = (db_session.query(model.DF_Module.na_id,
                                               model.DeviceFeature.df_type,
                                               model.DeviceFeature.df_name)
                                        .select_from(model.DeviceObject)
                                        .join(model.DFObject)
                                        .join(model.DF_Module)
                                        .join(model.DeviceFeature)
                                        .filter(model.DeviceObject.do_id == do_id)
                                        .group_by(model.DF_Module.na_id,
                                                  model.DeviceFeature.df_id)
                                        .all())

                for na_id, df_type, df_name in na_records:
                    self.remove_link(na_id, mac_addr, df_type, df_name)

            # Clear DeviceObject's d_id
            (db_session.query(model.DeviceObject)
                       .filter(model.DeviceObject.do_id == do_id)
                       .update({'d_id': None}))
            db_session.commit()

        # auto bind simulator
        if check_sim:
            if str(do_id) in self._simulator:
                if getattr(self._simulator[str(do_id)], 'd_id'):
                    self.op_bind_device(ctx, do_id,
                                        self._simulator[str(do_id)].d_id,
                                        check_sim=False)

        return {'do_id': do_id}

    def _get_device_by_mac_addr(self, ctx, mac_addr):
        return ctx.db_session.query(model.Device).filter(
            model.Device.mac_addr == mac_addr).first()
