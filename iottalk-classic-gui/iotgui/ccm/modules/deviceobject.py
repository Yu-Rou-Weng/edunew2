"""
Device Object Module.

contains:

    op_create_device_object
    op_update_device_object
    op_delete_device_object
    op_get_device_object_info

    is_device_object_void
    is_device_object_exist
"""
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError
from iotgui.db import model

from iotgui import config


class DeviceObject(Interface):
    """DeviceObject class."""

    def op_create_device_object(self, ctx, p_id, dm_id, df):
        """
        Create new DeviceObject.

        :param p_id: <Project.p_id>
        :param dm_id: <DeviceModel.dm_id>
        :param df: a list of Device Feature name to create
        :type p_id: int
        :type dm_id: int
        :type df: List[<DeviceFeature.df_name>]

        :return:
            {
                'do_id': '<DeviceObject.do_id>'
            }
        """
        db_session = ctx.db_session

        # Create DeviceObject
        new_do = model.DeviceObject(
            p_id=p_id,
            dm_id=dm_id,
            d_id=None,
        )
        db_session.add(new_do)
        db_session.commit()

        # Create DFObject
        for df_name in df:
            df_record = (db_session.query(model.DeviceFeature)
                                   .filter(model.DeviceFeature.df_name == df_name)
                                   .first())
            self.op_create_device_feature_object(
                ctx, new_do.do_id, df_record.df_id, df_name)

        # create simulator
        if config.SIMTALK_ENDPOINT:
            if 'on' == self.op_get_simulation_status(ctx, p_id):
                self.create_simulator(ctx, new_do.do_id)

        # clear line color
        self.set_link_color(ctx, 'black', p_id=p_id)
        return {'do_id': new_do.do_id}

    def op_update_device_object(self, ctx, do_id, p_id, df):
        """
        Update DeviceObject.

        :param do_id: <DeviceObject.do_id>
        :param p_id: <Project.p_id>
        :param df: a list of Device Feature name to update
        :type do_id: int
        :type p_id: int
        :type df: List[<DeviceFeature.df_name>]

        :return:
            {
                'do_id': '<DeviceObject.do_id>'
            }
        """
        if not self.is_device_object_exist(ctx, do_id):
            raise CCMError('Device Object id {} not found'.format(do_id))

        db_session = ctx.db_session

        # check DeviceObject binded other user's device sensor
        # Issue: only allow bind other user's device for idf (by YB)
        check_odf = False
        device_record = (db_session.query(model.Device)
                                   .select_from(model.DeviceObject)
                                   .join(model.Device)
                                   .filter(model.DeviceObject.do_id == do_id)
                                   .first())
        if device_record and device_record.u_id != ctx.u_id:
            check_odf = True

        # Check remove or add DFObject
        # list of df_id which server saved
        origin_df_records = (db_session.query(model.DFObject)
                                       .select_from(model.DFObject)
                                       .filter(model.DFObject.do_id == do_id)
                                       .all())
        origin_df_id_set = set(
            [origin_df_record.df_id for origin_df_record in origin_df_records])

        # list of df_id which given df_name by user
        modify_df_records = (db_session.query(model.DeviceFeature)
                                       .filter(model.DeviceFeature.df_name.in_(df))
                                       .all())
        modify_df_id_set = set(
            [modify_df_record.df_id for modify_df_record in modify_df_records])

        # check output dfo with binded other user's device sensor
        # Issue: only allow bind other user's device for idf (by YB)
        if check_odf:
            for modify_df_record in modify_df_records:
                if modify_df_record.df_type == 'output':
                    raise CCMError('The binded device cannot be use for odf')

        # add new DFObject
        new_df_id_set = modify_df_id_set.difference(origin_df_id_set)
        for df_id in sorted(new_df_id_set):
            df_name, = (db_session.query(model.DeviceFeature.df_name)
                                  .filter(model.DeviceFeature.df_id == df_id)
                                  .first())
            self.op_create_device_feature_object(ctx, do_id, df_id, df_name)

        # delete DFObject
        delete_df_id_set = origin_df_id_set.difference(modify_df_id_set)
        for df_id in sorted(delete_df_id_set):
            dfo_record = (db_session.query(model.DFObject)
                                    .filter(model.DFObject.do_id == do_id,
                                            model.DFObject.df_id == df_id)
                                    .first())
            self.op_delete_device_feature_object(ctx, dfo_record.dfo_id, do_id)

        # clear line color
        self.set_link_color(ctx, 'black', p_id=p_id)
        return {'do_id': do_id}

    def op_delete_device_object(self, ctx, do_id):
        """
        Delete a Device Object by given dm_id.

        If the Device Object has links to Network Application,
        server will remove the links, too.

        :param do_id: <DeviceObject.do_id>
        :type do_id: int

        :return:
            {
                'do_id': '<DeviceObject.do_id>'
            }
        """
        if not self.is_device_object_exist(ctx, do_id):
            raise CCMError('Device Object id {} not found'.format(do_id))

        db_session = ctx.db_session

        # delete DFObject
        dfo_records = (db_session.query(model.DFObject)
                                 .filter(model.DFObject.do_id == do_id)
                                 .all())
        for dfo_record in dfo_records:
            self.op_delete_device_feature_object(ctx,
                                                 dfo_record.dfo_id,
                                                 do_id,
                                                 False)

        # delete DeviceObject
        (db_session.query(model.DeviceObject)
                   .filter(model.DeviceObject.do_id == do_id)
                   .delete())
        db_session.commit()

        # delete simulator
        self.delete_simulator(ctx, do_id)

        return {'do_id': do_id}

    def op_get_device_object_info(self, ctx, do_id, p_id):
        """
        Get the Device Object's information detail.

        :param do_id: <DeviceObject.do_id>
        :param p_id: <Project.p_id>
        :type do_id: int
        :type p_id: int

        :return:
            {
                <DeviceModel>,
                'do': {
                    'do_id': do_id,
                    'dfo': [ '<DeviceFeature.df_name>', ...],
                    'extra_setup_webpage': <Device.extra_setup_webpage>
                }
            }
        """
        db_session = ctx.db_session

        # query DeviceModel
        do_record = (db_session.query(model.DeviceObject)
                               .filter(model.DeviceObject.do_id == do_id)
                               .first())
        if not do_record:
            raise CCMError('Device Object id {} not found'.format(do_id))

        result = self.op_get_device_model_info(ctx, do_record.dm_id)

        # query DFObject
        result['do'] = {'do_id': do_id, 'dfo': []}
        df_records = (db_session.query(model.DeviceFeature)
                                .select_from(model.DeviceObject)
                                .join(model.DFObject)
                                .join(model.DeviceFeature)
                                .filter(model.DeviceObject.do_id == do_id)
                                .all())
        for df_record in df_records:
            result['do']['dfo'].append(df_record.df_name)

        # query device extra_setup_webpage url for extra setting (ex: ML_device)
        if do_record.d_id:
            device_record = (db_session.query(model.Device)
                                       .filter(model.Device.d_id == do_record.d_id)
                                       .first())
            result['do']['extra_setup_webpage'] = device_record.extra_setup_webpage

        # clear line color
        self.set_link_color(ctx, 'black', p_id=p_id)
        return result

    def is_device_object_void(self, ctx, do_id):
        """
        Check DeviceObject contains any DFObject.

        If DeviceObject has no DFObject, then delete it.

        :param do_id: <DeviceObject.do_id>
        :type do_id: int

        :return:
            None
        """
        db_session = ctx.db_session
        dfo_records = (db_session.query(model.DFObject)
                                 .filter(model.DFObject.do_id == do_id)
                                 .all())

        # if no DFObject, delete this DeviceObject
        if not dfo_records:
            self.op_delete_device_object(ctx, do_id)

    def is_device_object_exist(self, ctx, do_id) -> bool:
        x = (ctx.db_session
                .query(model.DeviceObject)
                .filter(model.DeviceObject.do_id == do_id)
                .first())
        return x is not None
