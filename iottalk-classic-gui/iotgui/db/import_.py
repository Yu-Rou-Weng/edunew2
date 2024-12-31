#!/usr/bin/env python3
import json

from sys import argv

from iotgui.ccm.modules.utils import Context
from iotgui.ccm.mqttclient import mqtt_module as ccm
from iotgui.config import TYPE_LIST
from iotgui.db import connect, session_scope

fn_dict = {}  # 'fn_name': 'fn_id'
df_dict = {}  # 'df_name': 'df_id'
tag_dict = {}  # 'tag_name': 'tag_id'


# check part
def check_device_feature_parameter(dfp):
    """Check DF_Parameter."""
    # check param_type, only allow the ypte in TYPE_LIST
    if dfp['param_type'] not in TYPE_LIST:
        raise Exception('"df_parameter\'s param_type" should in ' + TYPE_LIST)

    # check min, default 0
    dfp['min'] = dfp.get('min', 0)

    # check max, default 0
    dfp['max'] = dfp.get('max', 0)

    # check unit name, default 'None'
    unit_name = dfp.get('unit', 'None')
    if not unit_name:
        unit_name = 'None'

    with session_scope() as db_session:
        # set unit_id
        ctx = Context(None, db_session)
        dfp['unit_id'] = ccm.op_create_unit(ctx, unit_name).get('unit_id')

    return dfp


def check_device_feature(df):
    """Check DeviceFeature."""
    df_name = df.get('df_name')

    # Check df_name, if exist, ignore it and return false
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        if ccm.op_search_device_feature(ctx, df_name):
            print(df_name, 'is exist, IGNORE.')
            return False

    # Check df_type, only allow 'input'/'output'
    if df.get('df_type') not in ['input', 'output']:
        raise Exception(df_name + ': df_type only allow "input"/"output"')

    # check df_category, default 'Other'
    df['df_category'] = df.get('df_category', 'Other')
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        ccm.op_create_device_feature_category(ctx, df['df_category'])

    # check comment, default ''
    df['comment'] = df.get('comment', '')

    # check dfc
    if not isinstance(df.get('df_parameter'), list):
        raise Exception(df_name + ': "df_parameter" should be LIST.')
    if len(df.get('df_parameter')) == 0:
        raise Exception(
            df_name + ': "df_parameter" should contains AT LEAST ONE parameter.')

    # set default dfp
    for index, dfp in enumerate(df.get('df_parameter')):
        df['df_parameter'][index] = check_device_feature_parameter(dfp)

    return True


# imoprt part
def import_device_feature_category(dfc):
    print('[DeviceFeatureCategory]', dfc['dfc_name'])
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        return ccm.op_create_device_feature_category(ctx, **dfc)


def import_unit(unit):
    print('[Unit]', unit['unit_name'])
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        return ccm.op_create_unit(ctx, **unit)


def import_function(function):
    print('[Function]', function['fn_name'])
    function['df_id'] = function.get('df_id', None)
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        return ccm.op_create_function(ctx, **function)


def import_function_sdf(function_sdf):
    data = {
    }
    for fn in function_sdf.get('fn_list', []):
        data = {
            'df_id': df_dict.get(function_sdf.get('df_name')),
            'fn_id': fn_dict.get(fn.get('fn_name'))
        }
        with session_scope() as db_session:
            ctx = Context(None, db_session)
            ccm.op_create_functionSDF(ctx, **data)


def import_device_feature(df):
    print('[DeviceFeature]', df['df_name'])
    if not check_device_feature(df):
        return

    with session_scope() as db_session:
        ctx = Context(None, db_session)
        # create new df
        return ccm.op_create_device_feature(ctx, **df)


def import_device_model(dm):
    dm_name = dm.get('dm_name')
    print('[DeviceModel]', dm_name)
    # Check dm_name
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        if ccm.op_search_device_model(ctx, dm_name):
            print(dm_name, 'is exist, IGNORE.')
            return

    # check df_list
    if not isinstance(dm.get('df_list'), list):  # df_list should be list
        raise Exception(dm_name + ': "df_list" should be LIST.')
    if len(dm.get('df_list')) == 0:  # df_list should not empty
        raise Exception(dm_name + ': "df_list" should contains AT LEAST ONE df.')

    # check all device feature info
    for index, df in enumerate(dm.get('df_list')):
        if isinstance(df, str):  # use device feature name to ref
            # get df_id
            with session_scope() as db_session:
                ctx = Context(None, db_session)
                df_id = ccm.op_search_device_feature(ctx, df)
            if not df_id:
                raise Exception('{}: unkonw df <{}>'.format(dm_name, df))

            # get device feature info
            with session_scope() as db_session:
                ctx = Context(None, db_session)
                df = ccm.op_get_device_feature_info(ctx, df_id)

        elif isinstance(df, dict):  # use customize device feature
            with session_scope() as db_session:
                ctx = Context(None, db_session)
                if ccm.op_search_device_feature(ctx,
                                                df.get('df_name')):  # device feature exist

                    # get df_id
                    df_id = ccm.op_search_device_feature(ctx, df['df_name'])

                    # get device feature info
                    df_tmp = ccm.op_get_device_feature_info(ctx, df_id)

                    # use customer info first, then default
                    for key in ['df_id', 'df_type', 'df_category', 'comment']:
                        df_tmp[key] = df.get(key, df_tmp[key])

                    # check device feature parameter
                    for index_dfp, (c_dfp, o_dfp) in enumerate(
                            zip(df.get('df_parameter', []), df_tmp.get('df_parameter'))):
                        o_dfp.update(c_dfp)
                        df_tmp['df_parameter'][index_dfp] = o_dfp

                else:  # device feature not exist
                    # get df_id
                    df_id = import_device_feature(df).get('df_id')

                    # get device feature info
                    df_tmp = ccm.op_get_device_feature_info(ctx, df_id)

                # check tag
                df_tmp['tags'] = []
                for tag in df.get("tags", []):
                    tag_id = tag_dict.get(tag)
                    if not tag_id:
                        raise Exception('{}.{}: unknown tag <{}>'.format(dm_name, df, tag))

                    df_tmp['tags'].append({'tag_id': tag_id})

                df = df_tmp
        else:
            raise Exception(dm_name + ': unknown device feature, must string or dict.')

        # update deivce feature info
        dm['df_list'][index] = df

    with session_scope() as db_session:
        ctx = Context(None, db_session)
        return ccm.op_create_device_model(ctx, **dm).get('dm_id')


def import_tag(tag):
    print('[Tag]', tag.get('tag_name'))
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        return ccm.op_create_tag(ctx, **tag)


def import_data(data):
    connect()

    for dfp in data.get('DeviceFeatureCategory', []):
        import_device_feature_category(dfp)

    for unit in data.get('Unit', []):
        import_unit(unit)

    for tag in data.get('Tag', []):
        tag_dict[tag['tag_name']] = str(import_tag(tag)['tag_id'])

    for fn in data.get('Function', []):
        import_function(fn)

    # set fn_dict
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        fn_list = ccm.op_get_function_list(ctx)
    for fn in fn_list.get('fn_list', []):
        fn_dict[str(fn['fn_name'])] = str(fn['fn_id'])

    for df in data.get('DeviceFeature', []):
        import_device_feature(df)

    # set df_dict
    with session_scope() as db_session:
        ctx = Context(None, db_session)
        df_list = ccm.op_get_device_feature_list(ctx)
    for df in df_list.get('input', []):
        df_dict[str(df['df_name'])] = str(df['df_id'])
    for df in df_list.get('output', []):
        df_dict[str(df['df_name'])] = str(df['df_id'])

    for fn_sdf in data.get('FunctionSDF', []):
        import_function_sdf(fn_sdf)

    for dm in data.get('DeviceModel', []):
        import_device_model(dm)


if __name__ == '__main__':
    if len(argv) > 1:
        with open(argv[1], 'r') as f:
            data = json.load(f)
            import_data(data)
    else:
        print('usage: python import_.py <import_file>')
