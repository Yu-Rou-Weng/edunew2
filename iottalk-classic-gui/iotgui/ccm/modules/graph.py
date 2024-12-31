#!/usr/bin/env python3
"""
Graph module.

contains:

    receive_graph_msg
    send_graph_msg
    attach_graph
    detach_graph
    add_link
    remove_link
    _get_normalize_code
    _add_funcs
    _set_join
    _set_link_func
    _set_join_func
"""
import json
import logging

from hashlib import sha256

from sqlalchemy import and_
from sqlalchemy.sql import func

from iotaa.client import Client as AAClient
from iotaa.client.exceptions import AAReadTimeout
from iotgui import config
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import Context, mqtt_server_thread
from iotgui.db import model, session_scope
from iotutils.aa.const import MosquittoPermission, ResponseCode

log = logging.getLogger("{}GRAPH\033[0m".format(config.LOG_COLOR_GRAPH))
log.setLevel(config.LOG_LEVEL_GRAPH)


class Graph(Interface):
    """Graph."""

    _graphs = set()  # na_id list

    @mqtt_server_thread
    def receive_graph_msg(self, client, userdata, msg):
        """Receive graph message handler."""
        log.debug("recv graph payload: {}".format(msg.payload.decode()))

        # TODO check graph
        payload = json.loads(msg.payload.decode())
        if (payload.get('op') == 'attach' and payload.get('state') == 'ok'):
            na_id = msg.topic.split('/')[-1]

            with session_scope() as db_session:
                fn_record = (
                    db_session.query(model.Function)
                              .select_from(model.MultipleJoin_Module)
                              .join(model.Function,
                                    model.Function.fn_id == model.MultipleJoin_Module.fn_id)
                              .filter(model.MultipleJoin_Module.na_id == na_id)
                              .first()
                )
                if fn_record:
                    # set temporary u_id
                    project_record = (
                        db_session.query(model.Project)
                                  .select_from(model.NetworkApplication)
                                  .join(model.Project)
                                  .filter(model.NetworkApplication.na_id == na_id)
                                  .first()
                    )

                    ctx = Context(project_record.u_id, db_session)
                    self._set_join(ctx, na_id, fn_record.fn_id)

        elif (payload.get('op') == 'detach' and payload.get('state') == 'ok'):
            na_id = msg.topic.split('/')[-1]
            log.debug('Graph detach, na_id: {}'.format(na_id))
        elif (payload.get('op') == 'start_monitor' and payload.get('state') == 'ok'):
            monitor_topics = payload.get('monitor_topics')

            # Get the credential ID of a GUI issued by the AA Subsystem
            gui_aa_credential_id = payload.get('aa_credential_id')
            response = {'op': 'anno', 'type': 'monitor_anno', 'data': monitor_topics, }

            if config.ENABLE_MQTT_AUTH:
                aa_client = \
                    AAClient(config.AA_HOST, config.AA_PORT, 'ccm', config.AA_TOKEN)

                try:
                    aa_response = \
                        aa_client.add_new_permission_rules(
                            gui_aa_credential_id,
                            [(monitor_topics, MosquittoPermission.SUBSCRIBE_READ, ), ]
                        )
                    assert aa_response.code == ResponseCode.OK
                except (AAReadTimeout, AssertionError, ):
                    response['data'] = ''

            client_id = payload.get('client_id')
            self.send_gui_msg(client_id, response)

    def send_graph_msg(self, na_id, payload):
        """Send graph message."""
        topic = config.MQTT.graph_req_topic.format(na_id)
        self.send_msg(topic, payload)

    def attach_graph(self, ctx, na_id):
        """Attach graph."""
        db_session = ctx.db_session
        na_id = str(na_id)
        # check project status
        na_record = (db_session.query(model.NetworkApplication)
                               .filter(model.NetworkApplication.na_id == na_id)
                               .first())
        if 'on' != self.op_get_project_status(ctx, na_record.p_id):
            return

        self.subscribe(config.MQTT.graph_res_topic.format(na_id))
        if na_id in self._graphs:
            return

        self._graphs.add(na_id)
        self.send_graph_msg(na_id, {'op': 'attach'})

    def detach_graph(self, na_id):
        """Detach graph."""
        na_id = str(na_id)
        if na_id in self._graphs:
            log.debug('send detach')
            self.send_graph_msg(na_id, {'op': 'detach'})
            self._graphs.remove(na_id)

    def _get_normalize_code(self, min_, max_, dfo_id, param_i):
        if min_ == max_:
            return None, None

        normalize_name = '_{}_{}_normalize'.format(dfo_id, param_i)
        # at the first time receive data, return the average of Max and Min
        normalize_code = """
_{dfo_id}_{param_i}_min = None
_{dfo_id}_{param_i}_max = None
def run(data):
    global _{dfo_id}_{param_i}_min, _{dfo_id}_{param_i}_max

    if _{dfo_id}_{param_i}_min is None:
        _{dfo_id}_{param_i}_min = data
    elif _{dfo_id}_{param_i}_min > data:
        _{dfo_id}_{param_i}_min = data

    if _{dfo_id}_{param_i}_max is None:
        _{dfo_id}_{param_i}_max = data
    elif _{dfo_id}_{param_i}_max < data:
        _{dfo_id}_{param_i}_max = data

    if _{dfo_id}_{param_i}_max == _{dfo_id}_{param_i}_min:
        return ({max} - {min}) / 2

    return (data - _{dfo_id}_{param_i}_min) * ({max} - {min}) / (_{dfo_id}_{param_i}_max - _{dfo_id}_{param_i}_min) + {min}""".format(  # noqa: E501
            dfo_id=dfo_id,
            min=min_,
            max=max_,
            param_i=param_i)

        return normalize_name, normalize_code

    def _add_funcs(self, ctx, na_id, df_type, fn_ids=[], normalize=[],
                   publish=True):
        main_code_temp = """
def run(*args):
    # user function
    result = []
{}
    return result
"""

        na_id = str(na_id)

        fn_digest_dict = {}
        fn_part_code = ''
        for idx, fn_id in enumerate(fn_ids):
            # basic function
            fn_info = (self.op_get_function_info(ctx, fn_id=fn_id))
            fn_code = fn_info['code']
            fn_name = fn_info['name']

            # normalize
            norm_name = None
            norm_code = None
            if idx < len(normalize) and normalize[idx] is not None:
                norm_name, norm_code = self._get_normalize_code(normalize[idx]['min'],
                                                                normalize[idx]['max'],
                                                                normalize[idx]['dfo_id'],
                                                                normalize[idx]['param_i'])
                if norm_name:
                    norm_digest = sha256(norm_code.encode('UTF-8')).hexdigest()
                    data = {
                        'op': 'add_funcs',
                        'codes': [norm_code],
                        'digests': [norm_digest]
                    }
                    if publish:
                        self.send_graph_msg(na_id, data)
                    norm_code = 'iot.{}({})'.format(norm_name, '{}')
                    fn_digest_dict.update({norm_name: norm_digest})

            if not fn_code:
                if df_type == 'idf':
                    fn_part_code = '    result = args'
                    break
                elif df_type == 'odf':
                    if norm_code:
                        fn_part_code += '    result.append({})\n'.format(
                            norm_code.format('args[min(len(args) - 1, {})]'.format(idx)))
                    else:
                        fn_part_code += \
                            '    result.append(args[min(len(args) - 1, {})])\n'.format(idx)
                    continue

            fn_name = '_' + fn_name
            fn_digest = sha256(fn_code.encode('UTF-8')).hexdigest()
            data = {
                'op': 'add_funcs',
                'codes': [fn_code],
                'digests': [fn_digest]
            }
            if publish:
                self.send_graph_msg(na_id, data)

            fn_digest_dict.update({fn_name: fn_digest})
            if df_type == 'odf':
                if norm_code:
                    fn_part_code += '    result.append({})\n'.format(
                        norm_code.format('iot.{}(*args)').format(fn_name))
                else:
                    fn_part_code += '    result.append(iot.{}(*args))\n'.format(fn_name)
            else:  # idf, join
                fn_part_code += '    result.append(iot.{}(*args))\n'.format(fn_name)

        main_code = main_code_temp.format(fn_part_code)
        main_digest = sha256(main_code.encode('UTF-8')).hexdigest()
        data = {
            'op': 'add_funcs',
            'codes': [main_code],
            'digests': [main_digest]
        }

        if publish:
            self.send_graph_msg(na_id, data)

        return main_digest, fn_digest_dict

    def add_link(self, ctx, na_id, dfo_id):
        """Add link."""
        db_session = ctx.db_session

        # check project status
        na_id = str(na_id)
        na_record = (db_session.query(model.NetworkApplication)
                               .filter(model.NetworkApplication.na_id == na_id)
                               .first())

        # check project is on
        if 'on' != self.op_get_project_status(ctx, na_record.p_id):
            return

        device_record = (db_session.query(model.Device.mac_addr,
                                          model.DeviceFeature.df_type,
                                          model.DeviceFeature.df_name,
                                          model.DeviceFeature.param_no)
                                   .select_from(model.DFObject)
                                   .join(model.DeviceObject)
                                   .join(model.Device)
                                   .join(model.DeviceFeature)
                                   .filter(model.DFObject.dfo_id == dfo_id)
                                   .first())

        na_record = (db_session.query(model.NetworkApplication)
                               .filter(model.NetworkApplication.na_id == na_id)
                               .first())

        if device_record and na_record:
            da_id, df_type, df_name, param_no = device_record
            df_type = 'idf' if (df_type == 'input') else 'odf'

            dfm_records = (db_session
                           .query(model.DF_Module)
                           .select_from(model.DF_Module)
                           .filter(and_(model.DF_Module.na_id == na_id,
                                        model.DF_Module.dfo_id == dfo_id))
                           .order_by(model.DF_Module.param_i.asc())
                           .all())

            idf_types = []
            fn_ids = []
            norms = []
            for index, dfm in enumerate(dfm_records):
                idf_types.append(dfm.idf_type)

                if df_type == 'idf' and index == 0:
                    fn_ids.append(dfm.fn_id)
                elif df_type == 'odf':
                    fn_ids.append(dfm.fn_id)
                    norms.append({'min': dfm.min,
                                  'max': dfm.max,
                                  'dfo_id': dfm.dfo_id,
                                  'param_i': dfm.param_i} if dfm.normalization else None)

            func_digest, func_depends = self._add_funcs(ctx, na_id, df_type, fn_ids, norms)

            # get tag length
            tag_record = (
                db_session.query(func.sum(model.Tag.param_no))
                          .select_from(model.DFObject)
                          .join(model.DeviceObject,
                                model.DeviceObject.do_id == model.DFObject.do_id)
                          .join(model.DM_DF,
                                and_(model.DM_DF.df_id == model.DFObject.df_id,
                                     model.DM_DF.dm_id == model.DeviceObject.dm_id))
                          .join(model.DM_DF_Tag,
                                model.DM_DF_Tag.mf_id == model.DM_DF.mf_id)
                          .join(model.Tag,
                                model.Tag.tag_id == model.DM_DF_Tag.tag_id)
                          .filter(model.DFObject.dfo_id == dfo_id)
                          .group_by(model.DFObject.dfo_id)
                          .first()
            )

            data = {
                'op': 'add_link',
                'da_id': da_id,
                df_type: df_name,
                'input_type': idf_types,
                'func': func_digest,
                'depends': func_depends,
                'param_no': param_no,
                'tag_param_no': int(tag_record[0]) if tag_record else 0,
            }

            self.send_graph_msg(na_id, data)

    def remove_link(self, na_id, da_id, df_type, df_name):
        """Remove link."""
        if not da_id:
            return

        na_id = str(na_id)
        df_type = 'idf' if (df_type == 'input') else 'odf'
        data = {
            'op': 'rm_link',
            'da_id': da_id,
            df_type: df_name
        }
        self.send_graph_msg(na_id, data)

    def _set_join(self, ctx, na_id, fn_id):
        if fn_id and fn_id != -1:  # fn_id is not None or empty
            na_id = str(na_id)
            func_digest, func_depends = self._add_funcs(ctx, na_id, 'join', [fn_id])
            data = {
                'op': 'set_join',
                'prev': None,
                'new': func_digest,
                'depends': func_depends,
            }
            self.send_graph_msg(na_id, data)

    def _set_link_func(self, ctx, na_id, dfo_id, new_funcs, idf_type, normalization=False):
        db_session = ctx.db_session
        na_id = str(na_id)
        device_record = (db_session.query(model.Device.mac_addr,
                                          model.DeviceFeature.df_type,
                                          model.DeviceFeature.df_name)
                                   .select_from(model.DFObject)
                                   .join(model.DeviceObject)
                                   .join(model.Device)
                                   .join(model.DeviceFeature)
                                   .filter(model.DFObject.dfo_id == dfo_id)
                                   .first())

        if device_record:
            da_id, df_type, df_name = device_record
            df_type = 'idf' if (df_type == 'input') else 'odf'

            dfm_records = (db_session.query(model.DF_Module)
                                     .select_from(model.DF_Module)
                                     .filter(and_(model.DF_Module.na_id == na_id,
                                                  model.DF_Module.dfo_id == dfo_id))
                                     .order_by(model.DF_Module.param_i.asc())
                                     .all())
            old_funcs = []
            old_norm = []
            for dfm in dfm_records:
                old_funcs.append(dfm.fn_id)

                if df_type == 'odf':
                    old_norm.append({'min': dfm.min,
                                     'max': dfm.max,
                                     'dfo_id': dfm.dfo_id,
                                     'param_i': dfm.param_i})

            if df_type == 'idf':
                old_funcs = [old_funcs[0]]
                new_funcs = [new_funcs[0]]

            if dfm_records[0].normalization:
                old_normalized_temp = old_norm
            else:
                old_normalized_temp = []

            old_fn_digest, old_fn_depends = self._add_funcs(ctx,
                                                            na_id,
                                                            df_type,
                                                            old_funcs,
                                                            old_normalized_temp,
                                                            False)
            if normalization:
                old_normalized_temp = old_norm
            else:
                old_normalized_temp = []

            new_fn_digest, new_fn_depends = self._add_funcs(ctx,
                                                            na_id,
                                                            df_type,
                                                            new_funcs,
                                                            old_normalized_temp)

            data = {
                'op': 'set_df_func',
                'da_id': da_id,
                df_type: df_name,
                'input_type': idf_type,
                'prev': old_fn_digest,
                'new': new_fn_digest,
                'depends': new_fn_depends
            }

            log.debug('[set_df_func] {}'.format(data))
            self.send_graph_msg(na_id, data)

    def _set_join_func(self, ctx, na_id, new_func_id):
        """
            'op': 'set_join',
            'prev': pre func digest,
            'new': new func digest,
            'depends': depends,
        """
        db_session = ctx.db_session
        na_id = str(na_id)

        fn_record = (db_session.query(model.MultipleJoin_Module.fn_id)
                               .select_from(model.MultipleJoin_Module)
                               .filter(model.MultipleJoin_Module.na_id == na_id)
                               .first())
        if fn_record[0] and new_func_id and new_func_id == fn_record[0]:
            return  # no change

        old_fn_digest = None
        new_fn_digest = None
        new_fn_depends = {}

        if fn_record[0] and int(fn_record[0]) >= 0:
            old_fn_digest, _ = self._add_funcs(ctx, na_id, 'join', [fn_record[0]])

        if new_func_id and int(new_func_id) >= 0:
            new_fn_digest, new_fn_depends = self._add_funcs(ctx, na_id, 'join',
                                                            [new_func_id])

        data = {
            'op': 'set_join',
            'prev': old_fn_digest,
            'new': new_fn_digest,
            'depends': new_fn_depends
        }

        log.debug('[set_join_func] {}'.format(data))
        self.send_graph_msg(na_id, data)
