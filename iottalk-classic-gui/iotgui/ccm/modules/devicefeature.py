"""
DeviceFeature Module.

contains:

    op_create_device_feature
    op_update_device_feature
    op_delete_device_feature
    op_get_device_feature_list
    op_get_device_feature_info
    op_search_device_feature
"""
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class DeviceFeature(Interface):
    """Device Feature class."""

    def op_create_device_feature(self, ctx, df_name, df_type, df_parameter,
                                 comment='', df_category='None'):
        """
        Create a new Device Feature, and return the new df_id.

        Server will check the Device Feature's name is duplicate or not.
        If duplicate, raise error.

        :param df_name: <DeviceFeature.df_name>
        :param df_type: <DeviceFeature.df_type>
        :param df_parameter: The device feature parameters (attributes)
        :param comment: <DeviceFeature.comment>, optional
        :param df_category: <DeviceFeature.df_category>, optional
        :type df_name: str
        :type df_type: str, in ['input', 'output']
        :type df_parameter: List[<DF_Parameter>]
        :type comment: str
        :type df_category: str

        :return:
            {
                'df_id': <DeviceFeature.df_id>
            }
        """
        db_session = ctx.db_session

        # check DeviceFeature name is in use
        if self.op_search_device_feature(ctx, df_name):
            raise CCMError('Device Feature "{}" already exists'.format(df_name))

        if df_type not in ('input', 'output'):
            raise CCMError('Invalid feature type "{}"'.format(df_type))

        if len(df_parameter) == 0:
            raise CCMError('df_parameter is empty')

        # Create new DeviceFeature
        new_df = model.DeviceFeature(
            df_name=df_name,
            df_type=df_type,
            param_no=len(df_parameter),
            comment=comment,
            df_category=df_category,
        )
        db_session.add(new_df)
        db_session.commit()

        # Create new DF_Parameter
        self.op_create_device_feature_parameter(
            ctx,
            df_id=new_df.df_id,
            df_parameter=df_parameter)

        return {'df_id': new_df.df_id}

    def op_update_device_feature(self, ctx, df_id, df_name, df_type,
                                 df_parameter, comment='', df_category='None'):
        """
        Update the Device Feature info.

        If success update, server will return df_id.

        :param df_id: <DeviceFeature.df_id>
        :param df_name: <DeviceFeature.df_name>
        :param df_type: <DeviceFeature.df_type>
        :param df_parameter: The device feature parameters (attributes)
        :param comment: <DeviceFeature.comment>, optional
        :param df_category: <DeviceFeature.df_category>, optional
        :type df_id: int
        :type df_name: str
        :type df_type: str, in ['input', 'output']
        :type df_parameter: List[<DF_Parameter>]
        :type comment: str
        :type df_category: str

        :return:
            {
                'df_id': <DeviceFeature.df_id>
            }
        """
        db_session = ctx.db_session

        # check DeviceFeature exist
        df_record = (db_session.query(model.DeviceFeature)
                               .filter(model.DeviceFeature.df_id == df_id)
                               .first())
        if not df_record:
            raise CCMError('Device Feature not found')

        # update DF_Parameter
        self.op_update_device_feature_parameter(
            ctx,
            df_id=df_id,
            df_parameter=df_parameter)

        # update fields
        df_record.df_type = df_type
        df_record.comment = comment
        df_record.df_category = df_category
        df_record.param_no = len(df_parameter)
        db_session.commit()

        return {'df_id': df_id}

    def op_delete_device_feature(self, ctx, df_id):
        """
        Delete a Device Feature by given df_id.

        Server will check the Device Feature is used or not.
        If delete successful, server will return df_id.

        :param df_id: <DeviceFeature.df_id>
        :type df_id: int

        :return:
            {
                'df_id': <DeviceFeature.df_id>
            }
        """
        db_session = ctx.db_session

        # check existence
        df = (db_session.query(model.DeviceFeature)
                        .filter(model.DeviceFeature.df_id == df_id)
                        .first())
        if df is None:
            raise CCMError('Device Feature id {} not found'.format(df_id))

        # check in use
        mf_records = (db_session.query(model.DM_DF)
                                .filter(model.DM_DF.df_id == df_id)
                                .all())
        dfo_records = (db_session.query(model.DFObject)
                                 .filter(model.DFObject.df_id == df_id)
                                 .all())

        if mf_records or dfo_records:
            raise CCMError('Device Feature is in use.')

        # delete DF_Parameter
        (db_session
            .query(model.DF_Parameter)
            .filter(model.DF_Parameter.df_id == df_id)
            .delete())

        # delete FunctionSDF
        (db_session
            .query(model.FunctionSDF)
            .filter(model.FunctionSDF.df_id == df_id)
            .delete())

        # delete DeviceFeature
        (db_session
            .query(model.DeviceFeature)
            .filter(model.DeviceFeature.df_id == df_id)
            .delete())
        db_session.commit()

        return {'df_id': df_id}

    def op_get_device_feature_list(self, ctx, df_category=None):
        """
        Get all Device Features (by category).

        Server will return two lists,
        input and output Device Feature list.

        If `df_category` is given, category will be used as search condition.

        :param df_category: <DeviceFeature.df_category>, optional
        :type df_category: str

        :return:
            {
                'input': [<DeviceFeature>, ...],
                'output': [<DeviceFeature>, ...]
            }
        """
        db_session = ctx.db_session

        condition = ()
        if df_category:
            # query category DeviceFeature
            condition = (model.DeviceFeature.df_category == df_category,)

        df_records = (db_session.query(model.DeviceFeature)
                                .filter(*condition)
                                .order_by(model.DeviceFeature.df_name)
                                .all())
        result = {
            'input': [],
            'output': []
        }
        for df_record in df_records:
            result[df_record.df_type].append(record_parser(df_record))

        return result

    def op_get_device_feature_info(self, ctx, df_id):
        """
        Get the Device Feature's information detail.

        :param df_id: <DeviceFeature.df_id>
        :type df_id: int

        :return:
            {
                'df_id': <DeviceFeature.df_id>,
                'df_name': <DeviceFeature.df_name>,
                'dt_type': <DeviceFeature.df_type>,
                'param_no': <DeviceFeature.param_no>, # number of parameters
                'comment': <DeviceFeature.comment>,
                'df_parameter': [<DF_Parameter>, ...]
            }
        """
        db_session = ctx.db_session

        # query DeviceFeature
        df_record = (db_session.query(model.DeviceFeature)
                               .filter(model.DeviceFeature.df_id == df_id)
                               .first())

        if not df_record:
            raise CCMError('Device Feature id {} not found'.format(df_id))

        df_info = record_parser(df_record)
        df_info['df_parameter'] = (self.op_get_device_feature_parameter(ctx, df_id)
                                       .get('df_parameter', []))

        return df_info

    def op_search_device_feature(self, ctx, df_name):
        """
        Seach Device Feature by name.

        If in use, return df_id, else return None.

        :param df_name: <DeviceFeature.df_name>
        :type df_name: str

        :return:
            <DeviceFeature.df_id> / None
        """
        db_session = ctx.db_session
        df_record = (db_session.query(model.DeviceFeature)
                               .filter(model.DeviceFeature.df_name == df_name)
                               .first())
        return (df_record.df_id if df_record else None)
