"""
DeviceModel Module.

contains:

    op_create_device_model
    op_update_device_model
    op_delete_device_model
    op_get_device_model_list
    op_get_device_model_info
    op_search_device_model
"""
from sqlalchemy import or_

from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class DeviceModel(Interface):
    """DeviceModel class."""

    def op_create_device_model(self, ctx, dm_name, df_list, dm_type='other',
                               plural=None, device_only=None):
        """
        Create a new Device Model.

        Server will check the dm_name is not duplicate,
        and return a new dm_id on success.

        :param dm_name: <DeviceModel.dm_name>
        :param df_list: a list of Device Feature info,
                        contains df_id, tags, df_parameter, etc
        :param dm_type: <DeviceModel.dm_type>, optional, legacy
        :param plural: The flag for this model's feature selection
                       Use the checkbox (False) on the GUI or
                       select (True), the default is False. Optional.
        :param device_only: The flag for click this model on the GUI.
                            Use the feature selection (False) or
                            device selection (True), the default is False.
                            Optional.
        :type dm_name: str
        :type df_list: List[<DeviceFeature>]
        :type dm_type: str
        :type plural: Boolean
        :type device_only: Boolean

        :return:
            {
                'dm_id': <DeviceModel.dm_id>
            }
        """
        db_session = ctx.db_session

        # check exist
        if self.op_search_device_model(ctx, dm_name):
            raise CCMError('Device Model "{}" already exists'.format(dm_name))

        # check df_list not empty
        if not df_list:
            raise CCMError('Feature list cannot be empty')

        # create new DeviceModel
        new_dm = model.DeviceModel(
            dm_name=dm_name,
            plural=plural or False,
            device_only=device_only or False)
        db_session.add(new_dm)
        db_session.commit()

        # TODO: check case of df_id not found

        # create new DM_DF and DF_Parameter
        for df in df_list:
            # create new DM_DF
            new_mf = model.DM_DF(
                dm_id=new_dm.dm_id,
                df_id=df['df_id'])
            db_session.add(new_mf)
            db_session.commit()

            # save DF_Parameter
            self.op_create_device_feature_parameter(
                ctx,
                mf_id=new_mf.mf_id,
                df_parameter=df['df_parameter'])

            # save DM_DF_Tag
            self.op_save_dm_df_tag(
                ctx,
                mf_id=new_mf.mf_id,
                tags=df.get('tags', []))

        return {'dm_id': new_dm.dm_id}

    def op_update_device_model(self, ctx, dm_id, dm_name, df_list,
                               dm_type='other', plural=None, device_only=None):
        """
        Update Device Model.

        Server will check the dm_name and dm_id is equal to DB,
        and check Device Model is not in use,
        then update and return the dm_id on success.

        :param dm_id: <DeviceModel.dm_id>
        :param dm_name: <DeviceModel.dm_name>
        :param df_list: a list of Device Feature info,
                        conains df_id, tags, df_parameter, etc
        :param dm_type: <DeviceModel.dm_type>, optional, legacy
        :param plural: The flag for this model's feature selection
                       Use the checkbox (False) on the GUI or
                       select (True). Optional.
        :param device_only: The flag for click this model on the GUI.
                            Use the feature selection or device selection.
                            Optional.
        :type dm_id: int
        :type dm_name: str
        :type plural: Boolean
        :type device_only: Boolean
        :type df_list: List[<DeviceFeature>]
        :type dm_type: str

        :return:
            {
                'dm_id': <DeviceModel.dm_id>
            }
        """
        db_session = ctx.db_session

        # check df_list not empty
        if not df_list:
            raise CCMError('Feature list cannot be empty')

        # check dm exist
        dm_record = (db_session.query(model.DeviceModel)
                               .filter(model.DeviceModel.dm_name == dm_name)
                               .first())
        if not dm_record:
            raise CCMError('Device Model not found')

        dm_id = dm_record.dm_id

        # check dm in use
        do_records = (db_session.query(model.DeviceObject)
                                .filter(model.DeviceObject.dm_id == dm_id)
                                .all())
        if do_records:
            raise CCMError('Device Model is in use.')

        # update plural
        if plural:
            dm_record.plural = plural
            db_session.commit()

        # update device_only
        if device_only:
            dm_record.device_only = device_only
            db_session.commit()

        # TODO: fix user setting mf
        old_mf_records = (db_session.query(model.DM_DF)
                                    .filter(model.DM_DF.dm_id == dm_id))
        old_mf_records = {mf.df_id: mf for mf in old_mf_records}
        # save DM_DF and DF_Parameter and DM_DF_Tag
        for df in df_list:
            if int(df['df_id']) in old_mf_records:
                old_mf_records.pop(int(df['df_id']))
            # update DF_Parameter
            self.op_update_device_feature_parameter(
                ctx,
                dm_id=dm_id,
                df_id=df['df_id'],
                df_parameter=df.get('df_parameter', []))

            # update new DM_DF_Tag
            self.op_save_dm_df_tag(
                ctx,
                dm_id=dm_id,
                df_id=df['df_id'],
                tags=df.get('tags', []))

        # delete not use DF_Parameter, DM_DF_Tag, DM_DF
        for mf in old_mf_records.values():
            (db_session.query(model.DF_Parameter)
                       .filter(model.DF_Parameter.mf_id == mf.mf_id)
                       .delete())
            (db_session.query(model.DM_DF_Tag)
                       .filter(model.DM_DF_Tag.mf_id == mf.mf_id)
                       .delete())
            (db_session.query(model.DM_DF)
                       .filter(model.DM_DF.mf_id == mf.mf_id)
                       .delete())
            db_session.commit()

        return {'dm_id': dm_id}

    def op_delete_device_model(self, ctx, dm_id):
        """
        Delete a Device Model by given dm_id.

        Server will check the Device Model is used or not,
        and return dm_id on success.

        :param dm_id: <DeviceModel.dm_id>
        :type dm_id: int

        :return:
            {
                'dm_id': <DeviceModel.dm_id>
            }
        """
        db_session = ctx.db_session

        # check exist
        dm_record = (db_session.query(model.DeviceModel)
                               .filter(model.DeviceModel.dm_id == dm_id)
                               .first())
        if not dm_record:
            raise CCMError('Device Model not found')

        # check in use
        do_records = (db_session.query(model.DeviceObject.dm_id)
                                .filter(model.DeviceObject.dm_id == dm_id)
                                .all())

        d_records = (db_session.query(model.Device.dm_id)
                               .filter(model.Device.dm_id == dm_id)
                               .all())
        if do_records or d_records:
            raise CCMError('Device Model is in use.')

        # delete DM_DF, DF_Parameter, DM_DF_Tag
        mf_records = (db_session.query(model.DM_DF)
                                .filter(model.DM_DF.dm_id == dm_id)
                                .all())
        for mf_record in mf_records:
            self.op_delete_device_feature_parameter(ctx, mf_id=mf_record.mf_id)
            self.op_delete_dm_df_tag(ctx, mf_id=mf_record.mf_id)
            db_session.delete(mf_record)
            db_session.commit()

        db_session.delete(dm_record)
        db_session.commit()

        return {'dm_id': dm_id}

    def op_get_device_model_list(self, ctx):
        """
        Get list of all device models without device features info.

        :return:
            {
                'dm_list': [<DeviceModel>, ...]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        dm_records = (db_session.query(model.DeviceModel)
                                .select_from(model.DeviceModel)
                                .join(model.DM_DF)
                                .join(model.DF_Parameter)
                                .filter(or_(model.DF_Parameter.u_id == u_id,
                                            model.DF_Parameter.u_id.is_(None)))
                                .group_by(model.DeviceModel.dm_id)
                                .order_by(model.DeviceModel.dm_name)
                                .all())

        dm_list = []
        for dm_record in dm_records:
            dm_list.append(record_parser(dm_record))

        return {'dm_list': dm_list}

    def op_get_device_model_info(self, ctx, dm_id):
        """
        Get single device model info, like name and device features.

        :param dm_id: <DeviceModel.dm_id>
        :type dm_id: int

        :return:
            {
                <DeviceModel>,
                'df_list': [ <DeviceFeature>, ...] # with tag_id
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # query DeviceModel
        dm_record = (db_session.query(model.DeviceModel)
                               .filter(model.DeviceModel.dm_id == dm_id)
                               .first())
        if dm_record is None:
            raise CCMError('Device Model id "{}" not found'.format(dm_id))

        dm = record_parser(dm_record)
        dm['df_list'] = []

        # query DeviceFeature
        df_records = (db_session.query(model.DeviceFeature)
                                .select_from(model.DM_DF)
                                .join(model.DeviceFeature,
                                      model.DeviceFeature.df_id == model.DM_DF.df_id)
                                .join(model.DF_Parameter,
                                      model.DF_Parameter.mf_id == model.DM_DF.mf_id)
                                .filter(model.DM_DF.dm_id == dm_id,
                                        or_(model.DF_Parameter.u_id == u_id,
                                            model.DF_Parameter.u_id.is_(None)))
                                .group_by(model.DeviceFeature.df_id)
                                .order_by(model.DeviceFeature.df_name)
                                .all())

        for df_record in df_records:
            df = record_parser(df_record)
            df['df_parameter'] = self.op_get_device_feature_parameter(
                ctx,
                df_id=df['df_id'],
                dm_id=dm_id)['df_parameter']
            df.update(self.op_get_dm_df_tag(
                ctx,
                df_id=df['df_id'],
                dm_id=dm_id))

            dm['df_list'].append(df)

        return dm

    def op_search_device_model(self, ctx, dm_name):
        """
        Check DeviceModel name is in use.

        :param dm_name: <DeviceModel.dm_name>

        :return:
            <DeviceModel.dm_id> / None
        """
        dm_record = (ctx.db_session
                        .query(model.DeviceModel)
                        .filter(model.DeviceModel.dm_name == dm_name)
                        .first())
        return (dm_record.dm_id if dm_record else None)
