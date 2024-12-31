"""
Device Feature Object Module.

contains:

    op_create_device_feature_object
    op_update_device_feature_object
    op_delete_device_feature_object
    op_get_device_feature_object_info
    op_get_alias_name
    op_set_alias_name
"""
from sqlalchemy import and_

from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class DeviceFeatureObject(Interface):
    """DeviceObject class."""

    def op_create_device_feature_object(self, ctx, do_id, df_id, alias_name):
        """
        Create a new Device Feature Object to the Device Object.

        :param do_id: <DeviceObject.do_id>
        :param df_id: <DeviceFeature.df_id>
        :param alias_name: <DFObject.alias_name>
        :type do_id: int
        :type df_id: int
        :type alias_name: str

        :return:
            {
                'dfo_id': '<DFObject.dfo_id>'
            }
        """
        db_session = ctx.db_session

        # create DFObject
        new_dfo = model.DFObject(
            do_id=do_id,
            df_id=df_id,
            alias_name=alias_name,
        )
        db_session.add(new_dfo)
        db_session.commit()

        return {'dfo_id': new_dfo.dfo_id}

    def op_update_device_feature_object(self, ctx, dfo_id, alias_name,
                                        df_parameter):
        """
        Update the Device Feature information
        by correspondence Device Feature Object.

        :param dfo_id: <DFObject.dfo_id>
        :param alias_name: <DFObject.alias_name>, set to new alias name
        :param df_parameter: a list of df_parameter
        :type dfo_id: int
        :type alias_name: str
        :type df_parameter: List[<DF_Parameter>]

        :return:
            {
                'dfo_id': '<DFObject.dfo_id>'
            }
        """
        db_session = ctx.db_session

        # Check DM_DF exist
        mf_record = (
            db_session.query(model.DM_DF)
                      .select_from(model.DFObject)
                      .join(model.DeviceObject)
                      .outerjoin(model.DM_DF,
                                 and_(model.DM_DF.df_id == model.DFObject.df_id,
                                      model.DM_DF.dm_id == model.DeviceObject.dm_id))
                      .filter(model.DFObject.dfo_id == dfo_id)
                      .first()
        )
        if not mf_record:
            raise CCMError('Device Feature for the Device Model not find.')

        # Update DF_Parameter
        self.op_update_device_feature_parameter(
            ctx,
            mf_id=mf_record.mf_id,
            df_parameter=df_parameter)

        # Update alias_name
        (db_session
            .query(model.DFObject)
            .filter(model.DFObject.dfo_id == dfo_id)
            .update({'alias_name': alias_name}))
        db_session.commit()

        return {'dfo_id': dfo_id}

    def op_delete_device_feature_object(self, ctx, dfo_id, do_id,
                                        check_do_valid=True):
        """
        Delete DFObject.

        :param dfo_id: <DFObject.dfo_id>
        :param do_id: <DeviceObject.do_id>
        :param check_do_valid: Check DeviceObject is void or not.
        :type dfo_id: int
        :type do_id: int
        :type check_do_valid: boolean

        :return:
            {
                'dfo_id': '<DFObject.dfo_id>',
                'do_id': '<DeviceObject.do_id>'
            }
        """
        db_session = ctx.db_session

        # remove DF_Module (link)
        dfm_records = (db_session.query(model.DF_Module)
                                 .filter(model.DF_Module.dfo_id == dfo_id)
                                 .group_by(model.DF_Module.na_id)
                                 .all())
        for dfm_record in dfm_records:
            self.op_delete_link(ctx, dfm_record.na_id, dfo_id)

        # remove DFObject
        (db_session.query(model.DFObject)
                   .filter(model.DFObject.dfo_id == dfo_id)
                   .delete())
        db_session.commit()

        # check void DeviceObject
        if check_do_valid:
            self.is_device_object_void(ctx, do_id)

        return {'dfo_id': dfo_id, 'do_id': do_id}

    def op_get_device_feature_object_info(self, ctx, dfo_id, p_id):
        """
        Get DeviceFeature detail info by DFObject.

        :param dfo_id: <DFObject.dfo_id>
        :param p_id: <Project.p_id>
        :type dfo_id: int
        :type p_id: int

        :return:
            {
                'dfo_id': '<DFObject.dfo_id>',
                'df_id': '<DeviceFeature.df_id>',
                'df_type': '<DeviceFeature.df_type>',
                'alias_name': '<DeviceObject.alias_name>',
                'dm_name': '<DeviceModel.dm_name>',
                'df_mapping_func': [ <Function>, ...],
                'df_parameter': [ <DF_Parameter>, ...]
            }
        """
        db_session = ctx.db_session

        # get basic info
        dfo_record = (
            db_session.query(model.DFObject.dfo_id,
                             model.DFObject.alias_name,
                             model.DFObject.df_id,
                             model.DeviceModel.dm_name,
                             model.DeviceFeature.df_type,
                             model.DM_DF.mf_id)
                      .select_from(model.DFObject)
                      .join(model.DeviceObject)
                      .join(model.DeviceModel)
                      .join(model.DeviceFeature)
                      .join(model.DM_DF,
                            and_(model.DM_DF.df_id == model.DFObject.df_id,
                                 model.DM_DF.dm_id == model.DeviceModel.dm_id))
                      .filter(model.DFObject.dfo_id == dfo_id)
                      .first()
        )
        if not dfo_record:
            raise CCMError('Device Feature Object not find.')

        result = record_parser(dfo_record)
        result['df_mapping_func'] = (
            self.op_get_device_feature_function_list(ctx, dfo_record.df_id)
                .get('fn_list', [])
        )
        result['df_parameter'] = (
            self.op_get_device_feature_parameter(ctx, mf_id=dfo_record.mf_id)
                .get('df_parameter', [])
        )

        # clear line color
        self.set_link_color(ctx, 'black', p_id=p_id)
        return result

    def op_get_alias_name(self, ctx, mac_addr, df_name):
        """
        Get DeviceFeatureObject's alias_name.

        :param mac_addr: <Device.mac_addr>
        :param df_name: <DeviceFeature.df_name>
        :type mac_addr: str
        :type df_name: str

        :return:
            {
                'alias_name': <DFObject.alias_name>
            }
        """
        db_session = ctx.db_session
        dfo_record = (db_session.query(model.DFObject)
                                .select_from(model.Device)
                                .filter(model.Device.mac_addr == mac_addr)
                                .join(model.DeviceObject)
                                .join(model.DFObject)
                                .join(model.DeviceFeature)
                                .filter(model.DeviceFeature.df_name == df_name)
                                .first())

        if not dfo_record:
            raise CCMError('alias_name not find')

        return {'alias_name': dfo_record.alias_name}

    def op_set_alias_name(self, ctx, mac_addr, df_name, alias_name):
        """
        Set DeviceFeatureObject's alias_name.

        :param mac_addr: <Device.mac_addr>
        :param df_name: <DeviceFeature.df_name>
        :param alias_name: <DFObject.alias_name>
        :type mac_addr: str
        :type df_name: str
        :type alias_name: str

        :return:
            {
                'alias_name': <DFObject.alias_name>
            }
        """
        db_session = ctx.db_session
        # check exist
        dfo_record = (db_session.query(model.DFObject)
                                .select_from(model.Device)
                                .filter(model.Device.mac_addr == mac_addr)
                                .join(model.DeviceObject)
                                .join(model.DFObject)
                                .join(model.DeviceFeature)
                                .filter(model.DeviceFeature.df_name == df_name)
                                .first())

        if not dfo_record:
            raise CCMError('alias_name not find')

        # udpate
        (db_session
            .query(model.DFObject)
            .filter(model.DFObject.dfo_id == dfo_record.dfo_id)
            .update({'alias_name': alias_name}))
        db_session.commit()

        # announce all gui client
        self.gui_broadcast({'op': 'anno',
                            'type': 'change_alias',
                            'data': {'dfo_id': dfo_record.dfo_id}})

        return {'alias_name': alias_name}
