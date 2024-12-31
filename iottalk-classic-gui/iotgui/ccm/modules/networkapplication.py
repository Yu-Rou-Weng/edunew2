"""
NetworkApplication Module.

contains:

    op_create_na
    op_update_na
    op_delete_na
    op_get_na_list
    op_get_na_info
    op_get_na_monitor
    op_create_link
    op_delete_link

    set_link_color
    is_na_complete
"""
from sqlalchemy import and_, func

from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class NetworkApplication(Interface):
    """NetworkApplication class."""

    def op_create_na(self, ctx, p_id, na_name, na_idx, dfo_ids):
        """
        Create a new NetworkApplication.

        :param p_id: <Project.p_id>
        :param na_name: <NetworkApplication.na_name>
        :param na_idx: <NetworkApplication.na_idx>, GUI index
        :param dfo_ids: a list of Device Object ID which link to this na
                        at least 2 to create
        :type p_id: int
        :type na_name: str
        :type na_idx: int
        :type dfo_ids: List[<DFObject.dfo_id>]

        :return:
            {
                'na_id': '<NetworkApplication.na_id>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        self.is_project_owner(db_session, u_id, p_id, throw_err=True)

        # check tag
        dfo_tag_records = (
            db_session.query(model.DM_DF_Tag)
                      .select_from(model.DFObject)
                      .join(model.DeviceObject,
                            model.DeviceObject.do_id == model.DFObject.do_id)
                      .join(model.DM_DF,
                            and_(model.DM_DF.dm_id == model.DeviceObject.dm_id,
                                 model.DM_DF.df_id == model.DFObject.df_id))
                      .join(model.DM_DF_Tag,
                            model.DM_DF_Tag.mf_id == model.DM_DF.mf_id)
                      .filter(model.DFObject.dfo_id.in_(dfo_ids))
                      .all()
        )
        dfo_tag_set = set()
        for dfo_tag_record in dfo_tag_records:
            dfo_tag_set.add(dfo_tag_record.tag_id)

        if len(dfo_tag_records) != len(dfo_tag_set) * 2:
            # if two dfo has the same tags, the tag_id should appears twice
            raise CCMError('NetworkApplication should use the Features with the same Tag.')

        # create new NetworkApplication
        new_na = model.NetworkApplication(
            na_name=na_name,
            na_idx=na_idx,
            p_id=p_id,
        )
        db_session.add(new_na)
        db_session.commit()

        # attach esm graph
        self.attach_graph(ctx, new_na.na_id)

        # add link
        for dfo_id in dfo_ids:
            self.op_create_link(ctx, new_na.na_id, dfo_id, check_tag=False)

        return {'na_id': new_na.na_id}

    def op_update_na(self, ctx, na_id, na_name=None, dfm_list=[],
                     multiplejoin_fn_id=None):
        """
        Update the Network Application.

        Update the Function used,
        the Multiple Join Function used,
        or the Multiple Join's Device Feature index.

        :param na_id: <NetworkApplication.na_id>
        :param na_name: <NetworkApplication.na_name>
        :param dfm_list: the list of Device Feauture Module info,
                         update the function used by given dfo_id
        :param multiplejoin_fn_id: <Function.fn_id>
        :type na_id: int
        :type na_name: str
        :type dfm_list: List[<dfm_info>]
            <dfm_info> = {
                'dfo_id': '<DFObject.dfo_id>',
                'dfmp_list': [ <DF_Module>, ...]
            }
        :type multiplejoin_fn_id: int

        :return:
            {
                'na_id': '<NetworkApplication.na_id>'
            }
        """

        db_session = ctx.db_session

        # check login user is na owner
        na_record = (db_session.query(model.NetworkApplication)
                               .select_from(model.NetworkApplication)
                               .join(model.Project)
                               .filter(model.NetworkApplication.na_id == na_id,
                                       model.Project.u_id == ctx.u_id)
                               .first())
        if not na_record:
            raise CCMError('NetworkApplication not find.')

        # Update DF_Module
        for dfm in dfm_list:
            fn_list = [dfmp.get('fn_id', None) for dfmp in dfm['dfmp_list']]
            idf_type = [dfmp.get('idf_type', 'sample') for dfmp in dfm['dfmp_list']]

            # update graph function (na_id, dfo_id, new_fn_list, normalization)
            # this setting should be called before update database,
            # cause this function will check the data change between
            # database and user update.
            self._set_link_func(ctx, na_id, dfm['dfo_id'], fn_list, idf_type,
                                dfm['dfmp_list'][0].get('normalization', False))

            # update database
            for dfmp in dfm['dfmp_list']:
                (db_session
                    .query(model.DF_Module)
                    .filter(
                        model.DF_Module.na_id == na_id,
                        model.DF_Module.dfo_id == dfm['dfo_id'],
                        model.DF_Module.param_i == dfmp['param_i'])
                    .update(dfmp))

        # Update NetworkApplication name
        if na_name:
            (db_session
                .query(model.NetworkApplication)
                .filter(model.NetworkApplication.na_id == na_id)
                .update({'na_name': na_name}))

        # Update MultipleJoin_Module order
        # TODO

        # Update graph join function
        # this setting should be called before update database
        self._set_join_func(ctx, na_id, multiplejoin_fn_id)

        # Update MultipleJoin_Module function
        (db_session
            .query(model.MultipleJoin_Module)
            .filter(model.MultipleJoin_Module.na_id == na_id)
            .update({'fn_id': multiplejoin_fn_id}))
        db_session.commit()

        return {'na_id': na_id}

    def op_delete_na(self, ctx, na_id: int):
        """
        Delete a NetworkApplication.

        :param na_id: <NetworkApplication.na_id>

        :return:
            {
                'na_id': '<NetworkApplication.na_id>'
            }
        """
        # TODO: check login user is na owner

        db_session = ctx.db_session

        # delete link
        dfm_records = (db_session.query(model.DF_Module)
                                 .filter(model.DF_Module.na_id == na_id)
                                 .group_by(model.DF_Module.dfo_id)
                                 .all())
        for dfm_record in dfm_records:
            self.op_delete_link(ctx, na_id, dfm_record.dfo_id, False)

        # delete MultipleJoin_Module, actually this will delete by op_delete_link
        # but if there exist some error (like there is no data in DF_Module)
        # we still need to delete MultipleJoin_Module first
        (db_session
            .query(model.MultipleJoin_Module)
            .filter(model.MultipleJoin_Module.na_id == na_id)
            .delete())

        # delete na
        (db_session
            .query(model.NetworkApplication)
            .filter(model.NetworkApplication.na_id == na_id)
            .delete())
        db_session.commit()

        # detach esm graph
        self.detach_graph(na_id)

        return {'na_id': na_id}

    def op_get_na_list(self, ctx, p_id):
        """
        Get all Network Applications by Project with given p_id.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            {
                'p_id': <Project.p_id>,
                'na': [
                    {
                        'na_id': '<NetworkApplication.na_id>',
                        'na_name': '<NetworkApplication.na_name>',
                        'na_idx': '<NetworkApplication.na_idx>',
                        'input': [ <dfm_info>, ...],
                        'output': [ <dfm_info>, ...],
                    },
                    ...
                ]
            }

            <dfm_info>: {
                'dfo_id': '<DFObject.dfo_id>',
                'color': 'black' / 'red', # line color
                'df_type': '<DeviceFeature.df_type>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        self.is_project_owner(db_session, u_id, p_id, throw_err=True)

        result = {
            'p_id': p_id,
            'na': []
        }

        # query NetworkApplication info
        na_records = (db_session.query(model.NetworkApplication)
                                .select_from(model.NetworkApplication)
                                .filter(model.NetworkApplication.p_id == p_id))

        for na_record in na_records:
            na = record_parser(na_record)
            na['input'] = []
            na['output'] = []

            # query DF_Module info
            dfm_records = (db_session.query(model.DF_Module.dfo_id,
                                            model.DF_Module.color,
                                            model.DeviceFeature.df_type)
                                     .select_from(model.DF_Module)
                                     .join(model.DFObject)
                                     .join(model.DeviceFeature)
                                     .filter(model.DF_Module.na_id == na_record.na_id)
                                     .group_by(model.DF_Module.dfo_id)
                                     .all())

            for dfm_record in dfm_records:
                na[dfm_record.df_type].append(record_parser(dfm_record))

            result['na'].append(na)

        return result

    def op_get_na_info(self, ctx, na_id, p_id):
        """
        Get the Network Application's information detail.

        :param na_id: <NetworkApplication.na_id>
        :param p_id: <Project.p_id>
        :type na_id: int
        :type p_id: int

        :return:
            {
                'na_id': '<NetworkApplication.na_id>',
                'na_name': '<NetworkApplication.na_name>',
                'na_idx': '<NetworkApplication.na_idx',
                'input': [ <dfm_info>, ...],
                'output': [ <dfm_info>, ...],
                'multiple': [ <multiplejion_info>, ...]
                'fn_list': [ <fn_info>, ...] # for multiplejoin function
            }

            <dfm_info>:
                {
                    'dm_name': '<DeviceModel.dm_name>',
                    'dfo_id': '<DFObject.dfo_id>',
                    'alias_name': '<DFObject.alias_name>',
                    'fn_list': [ <fn_info>, ...]
                    'dfmp': [ <DF_Module>, ...],
                }

            <multiplejion_info>:
                {
                    'dfo_id': '<DFObject.dfo_id>',
                    'na_id': '<NetworkApplication.na_id>',
                    'param_i': 'integer',
                    'fn_id': '<Function.fn_id>'
                }

            <fn_info>:
                {
                    'fn_id': '<Function.fn_id>',
                    'fn_name': '<Function.fn_name>'
                }
        """
        db_session = ctx.db_session

        # get NetworkApplication info
        na_record = (db_session.query(model.NetworkApplication)
                               .filter(model.NetworkApplication.na_id == na_id)
                               .first())

        if not na_record:
            return None

        result = record_parser(na_record)
        result['fn_list'] = self.op_get_na_function_list(ctx).get('fn_list', [])
        result['input'] = []
        result['output'] = []
        result['multiple'] = []

        # get DF_Module info
        dfm_records = (db_session.query(model.DFObject.dfo_id,
                                        model.DFObject.alias_name,
                                        model.DFObject.df_id,
                                        model.DeviceFeature.df_type,
                                        model.DeviceFeature.df_name,
                                        model.DeviceModel.dm_name,
                                        model.Device.mac_addr,)
                                 .select_from(model.DF_Module)
                                 .join(model.DFObject)
                                 .join(model.DeviceFeature)
                                 .join(model.DeviceObject)
                                 .join(model.DeviceModel)
                                 .outerjoin(
                                     model.Device,
                                     model.Device.d_id == model.DeviceObject.d_id)
                                 .filter(model.DF_Module.na_id == na_id)
                                 .group_by(model.DFObject.dfo_id)
                                 .order_by(model.DFObject.do_id,
                                           model.DeviceFeature.df_name)
                                 .all())

        for dfm_record in dfm_records:
            dfm_tmp = record_parser(dfm_record)
            dfm_tmp['fn_list'] = self.op_get_device_feature_function_list(
                ctx, dfm_record.df_id).get('fn_list')
            dfm_tmp['dfmp'] = []

            dfmp_records = (db_session.query(model.DF_Module)
                                      .filter(model.DF_Module.dfo_id == dfm_record.dfo_id,
                                              model.DF_Module.na_id == na_id)
                                      .order_by(model.DF_Module.param_i)
                                      .all())

            for dfmp_record in dfmp_records:
                dfm_tmp['dfmp'].append(record_parser(dfmp_record))

            result[dfm_record.df_type].append(dfm_tmp)

        # get MultipleJoin_Module info
        multiplejoin_records = (db_session.query(model.MultipleJoin_Module)
                                          .select_from(model.MultipleJoin_Module)
                                          .filter(model.MultipleJoin_Module.na_id == na_id)
                                          .order_by(model.MultipleJoin_Module.param_i)
                                          .all())

        for multiplejoin_record in multiplejoin_records:
            result['multiple'].append(record_parser(multiplejoin_record))

        # set gui link color
        self.set_link_color(ctx, 'black', p_id=p_id)
        self.set_link_color(ctx, 'red', na_id=na_id)

        return result

    def op_get_na_monitor(self, ctx, na_id, p_id, aa_credential_id=None):
        """
        Get the Network Application's information detail.

        CCM will turn on the ESM to monitor mode,
        client will receive montitor topic from ESM later.

        :param na_id: <NetworkApplication.na_id>
        :param p_id: <Project.p_id>
        :param aa_credential_id: <The credential ID of a GUI issued by the AA Subsystem>
        :type na_id: int
        :type p_id: int
        :type aa_credential_id: int

        :return:
            {
                'na_id': '<NetworkApplication.na_id>',
                'input': [ <dfm_info>, ...],
                'output': [ <dfm_info>, ...],
            }

            <dfm_info>:
                {
                    'dfo_id': '<DFObject.dfo_id>',
                    'alias_name': '<DFObject.alias_name>',
                    'df_name': '<DFObject.df_name>',
                    'param_i': '<DFObject.param_i>',
                    'mac_addr': '<Device.mac_addr>',
                }
        """
        db_session = ctx.db_session

        # send start monitor control message to ESM
        self.send_graph_msg(
            na_id, {
                'op': 'start_monitor',
                'client_id': ctx.client_id,
                # The credential ID of a GUI issued by the AA Subsystem
                'aa_credential_id': aa_credential_id,
            })

        # get NetworkApplication info
        na_record = (db_session.query(model.NetworkApplication)
                               .filter(model.NetworkApplication.na_id == na_id)
                               .first())

        if not na_record:
            raise CCMError('NetworkApplication not find.')

        result = {
            'input': [],
            'output': []
        }

        # get DFObject info
        dfo_records = (db_session.query(model.DFObject.dfo_id,
                                        model.DFObject.alias_name,
                                        model.DeviceFeature.df_type,
                                        model.DeviceFeature.df_name,
                                        model.DeviceFeature.param_no,
                                        model.Device.mac_addr)
                                 .select_from(model.DF_Module)
                                 .join(model.DFObject)
                                 .join(model.DeviceFeature)
                                 .join(model.DeviceObject)
                                 .outerjoin(
                                     model.Device,
                                     model.Device.d_id == model.DeviceObject.d_id)
                                 .filter(model.DF_Module.na_id == na_id)
                                 .group_by(model.DFObject.dfo_id)
                                 .order_by(model.DFObject.do_id,
                                           model.DFObject.alias_name,
                                           model.DF_Module.param_i.desc())
                                 .all())

        for dfo_record in dfo_records:
            result[dfo_record.df_type].append(record_parser(dfo_record))

        # set gui link color
        self.set_link_color(ctx, 'black', p_id=p_id)
        self.set_link_color(ctx, 'red', na_id=na_id)

        return result

    def op_create_link(self, ctx, na_id, dfo_id, check_tag=True):
        """
        Add a new link from the Device Feature Object to the Network Application.

        Server will check the link is input or output.
        If link is input, server will set join function on esm
        to combine the input data.

        :param na_id: <NetworkApplication.na_id>
        :param dfo_id: <DFObject.dfo_id>
        :type na_id: int
        :type dfo_id: int

        :return:
            {
                'na_id': '<NetworkApplication.na_id>'
            }
        """
        db_session = ctx.db_session
        dfo_id = int(dfo_id)
        na_id = int(na_id)

        # check link exist
        dfm_record = (db_session.query(model.DF_Module)
                                .select_from(model.DF_Module)
                                .filter(model.DF_Module.na_id == na_id,
                                        model.DF_Module.dfo_id == dfo_id)
                                .first())

        if dfm_record:
            return {'na_id': na_id}

        # check tag
        if check_tag:
            dfo_tag_records = (
                db_session.query(model.DM_DF_Tag)
                          .select_from(model.DFObject)
                          .join(model.DeviceObject,
                                model.DeviceObject.do_id == model.DFObject.do_id)
                          .join(model.DM_DF,
                                and_(model.DM_DF.dm_id == model.DeviceObject.dm_id,
                                     model.DM_DF.df_id == model.DFObject.df_id))
                          .join(model.DM_DF_Tag,
                                model.DM_DF_Tag.mf_id == model.DM_DF.mf_id)
                          .filter(model.DFObject.dfo_id == dfo_id)
                          .all()
            )
            na_tag_records = (
                db_session.query(model.DM_DF_Tag)
                          .select_from(model.DF_Module)
                          .join(model.DFObject,
                                model.DFObject.dfo_id == model.DF_Module.dfo_id)
                          .join(model.DeviceObject,
                                model.DeviceObject.do_id == model.DFObject.do_id)
                          .join(model.DM_DF,
                                and_(model.DM_DF.df_id == model.DFObject.df_id,
                                     model.DM_DF.dm_id == model.DeviceObject.dm_id))
                          .join(model.DM_DF_Tag,
                                model.DM_DF_Tag.mf_id == model.DM_DF.mf_id)
                          .filter(model.DF_Module.na_id == na_id)
                          .group_by(model.DM_DF_Tag.tag_id)
                          .all()
            )
            dfo_tag_set = set()
            for dfo_tag in dfo_tag_records:
                dfo_tag_set.add(dfo_tag.tag_id)
            na_tag_set = set()
            for na_tag in na_tag_records:
                na_tag_set.add(na_tag.tag_id)
            if dfo_tag_set != dfo_tag_set:
                raise CCMError(
                    'NetworkApplication should use the Features with the same Tag.')

        # check df dm exist
        dfo_do_record = (db_session.query(model.DFObject.df_id, model.DeviceObject.dm_id)
                                   .select_from(model.DFObject)
                                   .join(model.DeviceObject,
                                         model.DeviceObject.do_id == model.DFObject.do_id)
                                   .filter(model.DFObject.dfo_id == dfo_id)
                                   .first())
        if not dfo_do_record:
            raise CCMError('can\'t find device feature object.')

        # copy DF_Parameter to DF_Module
        dfps = self.op_get_device_feature_parameter(
            ctx,
            df_id=dfo_do_record.df_id,
            dm_id=dfo_do_record.dm_id).get('df_parameter', [])
        for dfp in dfps:
            new_dfm = model.DF_Module(
                na_id=na_id,
                dfo_id=dfo_id,
                param_i=dfp.get('param_i'),
                idf_type=dfp.get('idf_type', 'sample'),
                fn_id=dfp.get('fn_id'),
                min=dfp.get('min'),
                max=dfp.get('max'),
                normalization=dfp.get('normalization'),
                color='black',
            )

            db_session.add(new_dfm)
        db_session.commit()

        # add input device to multiplejoin_module
        df_record = (db_session.query(model.DeviceFeature)
                               .select_from(model.DFObject)
                               .join(model.DeviceFeature)
                               .filter(model.DFObject.dfo_id == dfo_id)
                               .first())

        if df_record.df_type == 'input':
            multiplejoin_record = (
                db_session.query(func.max(model.MultipleJoin_Module.param_i).label('max_'),
                                 model.MultipleJoin_Module.fn_id)
                          .select_from(model.MultipleJoin_Module)
                          .filter(model.MultipleJoin_Module.na_id == na_id)
                          .first()
            )

            if multiplejoin_record.max_ is None:
                max_index = 0
            else:
                max_index = multiplejoin_record.max_ + 1

            # 2 links, set graph join function
            if max_index == 1:
                self._set_join(ctx, na_id, multiplejoin_record.fn_id)

            new_mjm = model.MultipleJoin_Module(
                na_id=na_id,
                param_i=max_index,
                dfo_id=dfo_id,
                fn_id=multiplejoin_record.fn_id,
            )
            db_session.add(new_mjm)
            db_session.commit()

        # add esm graph link
        self.add_link(ctx, na_id, dfo_id)

        return {'na_id': na_id}

    def op_delete_link(self, ctx, na_id, dfo_id, check_na_complete=True):
        """
        Remove the link from the Device Feature Object to the Network Application.

        Server will check the Network Application still have
        at least one input link and at least one output link,
        if not, remove this Network Application.

        :param dfo_id: <DFObject.dfo_id>
        :param na_id: <NetworkApplication.na_id>
        :param check_na_complete: check this na still contains idf and odf
        :type dfo_id: int
        :type na_id: int
        :type check_na_complete: boolean

        :return:
            {
                'dfo_id': '<DFObject.dfo_id>',
                'na_id': '<NetworkApplication.na_id>'
            }
        """
        db_session = ctx.db_session
        dfo_id = int(dfo_id)
        na_id = int(na_id)

        # get link info
        df_record = (db_session.query(model.Device.mac_addr,
                                      model.DeviceFeature.df_type,
                                      model.DeviceFeature.df_name)
                               .select_from(model.DF_Module)
                               .filter(model.DF_Module.na_id == na_id,
                                       model.DF_Module.dfo_id == dfo_id)
                               .join(model.DFObject)
                               .join(model.DeviceFeature)
                               .join(model.DeviceObject)
                               .outerjoin(model.Device,
                                          model.Device.d_id == model.DeviceObject.d_id)
                               .first())

        # delete DF_Module
        (db_session.query(model.DF_Module)
                   .filter(model.DF_Module.na_id == na_id,
                           model.DF_Module.dfo_id == dfo_id)
                   .delete())

        # Update graph join function to None, if the number of rest idf is one
        # this setting should be called before update database
        idf_records = (db_session.query(model.DeviceFeature)
                                 .select_from(model.DF_Module)
                                 .join(model.DFObject,
                                       model.DFObject.dfo_id == model.DF_Module.dfo_id)
                                 .join(model.DeviceFeature,
                                       model.DeviceFeature.df_id == model.DFObject.df_id)
                                 .filter(model.DF_Module.na_id == na_id,
                                         model.DeviceFeature.df_type == 'input')
                                 .group_by(model.DeviceFeature.df_id)
                                 .all())

        if len(idf_records) == 1:
            self._set_join_func(ctx, na_id, None)

        # delete MultipleJoin_Module
        (db_session.query(model.MultipleJoin_Module)
                   .filter(model.MultipleJoin_Module.na_id == na_id,
                           model.MultipleJoin_Module.dfo_id == dfo_id)
                   .delete())
        db_session.commit()

        # remove esm graph
        if df_record:
            self.remove_link(na_id,
                             df_record.mac_addr,
                             df_record.df_type,
                             df_record.df_name)

        # check join completely
        if check_na_complete:
            return self.is_na_complete(ctx, na_id)

        return {'na_id': na_id, 'dfo_id': dfo_id}

    def set_link_color(self, ctx, color='black', p_id=None, na_id=None):
        """
        Set link's color in project(s) or join.

        :param color: 'black' / 'red',
        :param p_id: <Project.p_id>, optional
        :param na_id: '<NetworkApplication.na_id>, optional
        :type color: str
        :type p_id: int
        :type na_id: int
        """
        db_session = ctx.db_session

        if p_id:
            dfm_records = (db_session.query(model.DF_Module)
                                     .select_from(model.NetworkApplication)
                                     .join(model.DF_Module)
                                     .filter(model.NetworkApplication.p_id == p_id)
                                     .all())
            for dfm_record in dfm_records:
                dfm_record.color = color

        elif na_id:
            (db_session.query(model.DF_Module)
                       .filter(model.DF_Module.na_id == na_id)
                       .update({'color': color}))

        db_session.commit()

    def is_na_complete(self, ctx, na_id):
        """
        Check NetworkApplication contains single side link.

        If Ture, call op_remove_na to remove this NetworkApplication.

        :param na_id: <NetworkApplication.na_id>
        :type na_id: int

        :return:
                {
                    'na_id': '<NetworkApplication.na_id>'
                }
        """
        db_session = ctx.db_session
        na_id = int(na_id)
        input_dfo_records = (db_session.query(model.DF_Module)
                                       .select_from(model.DF_Module)
                                       .join(model.DFObject, model.DeviceFeature)
                                       .filter(model.DF_Module.na_id == na_id,
                                               model.DeviceFeature.df_type == 'input')
                                       .all())

        output_dfo_records = (db_session.query(model.DF_Module.dfo_id)
                                        .select_from(model.DF_Module)
                                        .join(model.DFObject, model.DeviceFeature)
                                        .filter(model.DF_Module.na_id == na_id,
                                                model.DeviceFeature.df_type == 'output')
                                        .all())

        # if only one side line, delete join
        if not len(input_dfo_records) or not len(output_dfo_records):
            self.op_delete_na(ctx, na_id)
            return None

        return {'na_id': na_id}
