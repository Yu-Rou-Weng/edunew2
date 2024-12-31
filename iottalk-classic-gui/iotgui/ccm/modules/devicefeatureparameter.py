"""
Device Feature Parameter Module.

contains:

    op_create_device_feature_parameter
    op_update_device_feature_parameter
    op_delete_device_feature_parameter
    op_get_device_feature_parameter
"""
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class DeviceFeatureParameter(Interface):
    """DeviceFeatureParameter class."""

    def op_create_device_feature_parameter(self, ctx, df_parameter,
                                           df_id=None, dm_id=None, mf_id=None):
        """
        Create/Update Device Feature Parameters for DeviceFeature/DM_DF.

        Server will save for logging user.
        You need supply (`df_id`, `dm_id` ) or (`mf_id`) to create DM_DF,
        or (`df_id`) to create DeviceFeature.

        :param df_parameter: The device feature parameters (attributes)
        :param df_id: <DeviceFeature.df_id>, optional
        :param dm_id: <DeviceModel.dm_id>, optional
        :param mf_id: <DM_DF.mf_id>, optional
        :type df_parameter: List[<DF_Parameter>]
        :type df_id: int
        :type dm_id: int
        :type mf_id: int

        :return:
            {
                'df_id': '<DeviceFeature.df_id>',
                'mf_id': '<DM_DF.mf_id>',
            }
        """
        db_session = ctx.db_session

        # check query condition
        if df_id and dm_id:
            # if given df_id and dm_id, query mf_id first
            mf_record = (db_session.query(model.DM_DF)
                                   .filter(model.DM_DF.df_id == df_id,
                                           model.DM_DF.dm_id == dm_id)
                                   .first())
            if mf_record:
                mf_id = mf_record.mf_id
                df_id = None
            else:
                raise CCMError('Given "df_id" and "dm_id" not found.')
        elif not df_id and not mf_id:
            raise CCMError('one of "df_id" or "mf_id" should be supplied.')

        # save device feature parameter
        for idx, dfp in enumerate(df_parameter):
            new_dfp = model.DF_Parameter(
                mf_id=mf_id,
                df_id=df_id,
                param_type=dfp.get('param_type', 'int'),
                param_i=idx,
                idf_type=dfp.get('idf_type', 'sample'),
                fn_id=dfp.get('fn_id', None),
                min=dfp.get('min', 0),
                max=dfp.get('max', 0),
                unit_id=dfp.get('unit_id', 1),  # 1 for None
                u_id=None,
                normalization=dfp.get('normalization', 0),
            )
            db_session.add(new_dfp)
            db_session.commit()

        db_session.commit()

        return {'mf_id': mf_id} if mf_id else {'df_id': df_id}

    def op_update_device_feature_parameter(self, ctx, df_parameter,
                                           df_id=None, dm_id=None, mf_id=None):
        """
        Update Device Feature Parameters for DeviceFeature/DM_DF.

        Server will save for logging user.
        You need supply (`df_id`, `dm_id` ) or (`mf_id`) to update DM_DF,
        or (`df_id`) to update DeviceFeature.

        :param df_parameter: The device feature parameters (attributes)
        :param df_id: <DeviceFeature.df_id>, optional
        :param dm_id: <DeviceModel.dm_id>, optional
        :param mf_id: <DM_DF.mf_id>, optional
        :type df_parameter: List[<DF_Parameter>]
        :type df_id: int
        :type dm_id: int
        :type mf_id: int

        :return:
            {
                'df_id': '<DeviceFeature.df_id>',
                'mf_id': '<DM_DF.mf_id>',
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check query condition
        if mf_id:
            condition = (model.DF_Parameter.mf_id == mf_id)
        elif df_id and dm_id:
            # if given df_id and dm_id, query mf_id first
            mf_record = (db_session.query(model.DM_DF)
                                   .filter(model.DM_DF.df_id == df_id,
                                           model.DM_DF.dm_id == dm_id)
                                   .first())
            if mf_record:
                mf_id = mf_record.mf_id
                df_id = None
                condition = (model.DF_Parameter.mf_id == mf_id)
            else:
                # create new DM_DF
                new_mf = model.DM_DF(
                    dm_id=dm_id,
                    df_id=df_id)
                db_session.add(new_mf)
                db_session.commit()
                mf_id = new_mf.mf_id
                df_id = None
                condition = (model.DF_Parameter.mf_id == mf_id)
        elif df_id:
            condition = (model.DF_Parameter.df_id == df_id)
        else:
            raise CCMError('one of "df_id" or "mf_id" should be supplied.')

        # update device feature parameter
        for idx, dfp in enumerate(df_parameter):
            # try update first
            update_dfp = (db_session.query(model.DF_Parameter)
                                    .filter(condition,
                                            model.DF_Parameter.param_i == idx,
                                            model.DF_Parameter.u_id == u_id)
                                    .update(dfp))

            db_session.commit()

            # if return value is 0 means update 0 rows, so create new one
            if update_dfp == 0:
                new_dfp = model.DF_Parameter(
                    mf_id=mf_id,
                    df_id=df_id,
                    param_type=dfp.get('param_type', 'int'),
                    param_i=idx,
                    idf_type=dfp.get('idf_type', 'sample'),
                    fn_id=dfp.get('fn_id', None),
                    min=dfp.get('min', 0),
                    max=dfp.get('max', 0),
                    unit_id=dfp.get('unit_id', 1),  # 1 for None
                    u_id=u_id,
                    normalization=dfp.get('normalization', 0),
                )
                db_session.add(new_dfp)
                db_session.commit()

        # delete other parameter,
        # which param_i larger then number of given parameters
        (db_session.query(model.DF_Parameter)
                   .filter(condition,
                           model.DF_Parameter.u_id == u_id,
                           model.DF_Parameter.param_i >= len(df_parameter))
                   .delete())

        db_session.commit()

        return {'mf_id': mf_id} if mf_id else {'df_id': df_id}

    def op_delete_device_feature_parameter(self, ctx, df_id=None,
                                           dm_id=None, mf_id=None):
        """
        Delete Device Feature Parameters for DeviceFeature/DM_DF.

        You need supply (`df_id`, `dm_id` ) or (`mf_id`) to delete DM_DF,
        or (`df_id`) to delete DeviceFeature.

        :param df_id: <DeviceFeature.df_id>, optional
        :param dm_id: <DeviceModel.dm_id>, optional
        :param mf_id: <DM_DF.mf_id>, optional
        :type df_id: int
        :type dm_id: int
        :type mf_id: int

        :return:
            {
                'mf_id': mf_id,
                'df_id': df_id
            }
        """
        db_session = ctx.db_session

        if mf_id:
            condition = (model.DF_Parameter.mf_id == mf_id)
        elif df_id and dm_id:
            mf_record = (db_session.query(model.DM_DF)
                                   .filter(model.DM_DF.df_id == df_id,
                                           model.DM_DF.dm_id == dm_id)
                                   .first())
            if mf_record:
                mf_id = mf_record.mf_id
                df_id = None
                condition = (model.DF_Parameter.mf_id == mf_id)
            else:
                raise CCMError('can not find DM_DF for given dm_id and df_id.')
        elif df_id:
            condition = (model.DF_Parameter.df_id == df_id)
        else:
            raise CCMError('one of "df_id" or "mf_id" should be supplied.')

        (db_session.query(model.DF_Parameter)
                   .filter(condition)
                   .delete())
        db_session.commit()

        return {'mf_id': mf_id} if mf_id else {'df_id': df_id}

    def op_get_device_feature_parameter(self, ctx, df_id=None,
                                        dm_id=None, mf_id=None):
        """
        Get Device Feature Parameters for DeviceFeature/DM_DF.

        It will query logging user setting first then general setting.
        You need supply (`df_id`, `dm_id` ) or (`mf_id`) to query DM_DF,
        or (`df_id`) to query DeviceFeature.

        :param df_id: <DeviceFeature.df_id>, optional
        :param dm_id: <DeviceModel.dm_id>, optional
        :param mf_id: <DM_DF.mf_id>, optional
        :type df_id: int
        :type dm_id: int
        :type mf_id: int

        :return:
            {
                'df_parameter': [<DF_Parameter>, ...]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        if mf_id:
            condition = (model.DF_Parameter.mf_id == mf_id)
        elif df_id and dm_id:
            mf_record = (db_session.query(model.DM_DF)
                                   .filter(model.DM_DF.df_id == df_id,
                                           model.DM_DF.dm_id == dm_id)
                                   .first())
            if mf_record:
                mf_id = mf_record.mf_id
                df_id = None
                condition = (model.DF_Parameter.mf_id == mf_id)
            else:
                raise CCMError('can not find DM_DF for given dm_id and df_id.')
        elif df_id:
            condition = (model.DF_Parameter.df_id == df_id)
        else:
            raise CCMError('one of "df_id" or "mf_id" should be supplied.')

        # query user DF_Parameter
        dfp_records = (db_session.query(model.DF_Parameter)
                                 .filter(model.DF_Parameter.u_id == u_id, condition)
                                 .all())

        if not dfp_records:
            # query general DF_Parameter
            dfp_records = (db_session.query(model.DF_Parameter)
                                     .filter(condition,
                                             model.DF_Parameter.u_id.is_(None))
                                     .all())

        df_parameters = []
        for dfp_record in dfp_records:
            df_parameters.append(record_parser(dfp_record))

        return {'df_parameter': df_parameters}
