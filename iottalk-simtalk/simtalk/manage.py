# TODO: transaction.atomic for all function
import builtins
import random
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from .color import SimTalkColor
from .models import DeviceFeatureObject, DeviceObject, Project, SimStatus
from .models import Distribution, TimeDistribution, ValueDistribution
from .utils import start_simulator, ccmapi, stop_simulator, update_ccm_simulation

log = logging.getLogger(SimTalkColor.wrap(SimTalkColor.logger, 'SIMTALK'))
log.setLevel(level=logging.INFO)


def create_dfo(do_id, dfo_info):
    dfo_id = dfo_info['dfo_id']

    try:
        with transaction.atomic():
            # Create new DeviceFeatureObject record
            dfo = DeviceFeatureObject.objects.create(
                do_id_id=do_id,  # assign int to *_id instead of object
                dfo_id=dfo_id,
                df_name=dfo_info.get('alias_name')  # TOFIX: use df_name, not alias_name
            )

            # Create new TimeDistribution record
            td = TimeDistribution(
                dfo_id_id=dfo.dfo_id,  # assign int to *_id instead of object
                distribution=Distribution.NORMAL,
                max=10,
                min=1,
                mean=5,
                var=1,
                seed=random.randint(100000, 999999)
            )

            td.full_clean()
            td.save()

            for param in dfo_info['df_parameters']:
                # mean: use (min + max) / 2
                # var: TOFIX
                vd = ValueDistribution(
                    dfo_id_id=dfo.dfo_id,  # assign int to *_id instead of object
                    param_i=param.get('param_i'),
                    param_type=param.get('param_type'),
                    distribution=Distribution.UNIFORM,
                    max=param.get('max'),
                    min=param.get('min'),
                    mean=(param.get('max') + param.get('min')) / 2,
                    var=(param.get('max') - param.get('min')) / 2,
                    seed=random.randint(100000, 999999)
                )
                vd.full_clean()
                vd.save()
    except Exception as e:
        log.error(
            'Valid Error [dfo_id=%s, param_i=%s]: %s',
            dfo_id,
            param.get('param_i'),
            e
        )
        return False

    return True


def create_do(p_id, do_info, u_id):
    do_id = do_info.get('do_id')
    dm_name = do_info.get('dm_name')
    d_id = do_info.get('d_id')

    # Create new DeviceObject record.
    do = DeviceObject.objects.create(
        do_id=do_id,
        dm_name=dm_name,
        ccm_d_id=d_id,
        p_id_id=p_id  # assign int to *_id instead of object
    )

    # Get more DO detail from CCM.
    ccm_do = ccmapi(
        'deviceobject.get',
        {'p_id': p_id, 'do_id': do_id},
        u_id
    )

    for dfo in do_info['dfo']:
        # Get DF_Parameters from ccm_do by check the same df_name
        # TOFIX: shouldn't use alias_name
        df_parameters = list(filter(lambda x: x['df_name'] in dfo['alias_name'],
                                    ccm_do['df_list']))[0]['df_parameter']

        dfo['df_parameters'] = df_parameters
        create_dfo(do_id, dfo)
        # TODO: handle create fail.

    return True


def create_project(p_id, p_info, u_id):
    # Create new Project record.
    project = Project.objects.create(
        p_id=p_info.get('p_id'),
        p_name=p_info.get('p_name'),
        sim=p_info.get('sim'),
        u_id_id=p_info.get('u_id')  # assign int to *_id instead of object
    )

    # Create new DeviceObject records, only ido for simulation.
    sync_dos(p_id, p_info.get('ido', []), u_id)

    return True


def sync_dfos(p_id, do_id, ccm_dfos, u_id):
    # sync DeviceFeatureObject
    sim_dfos = DeviceFeatureObject.objects.filter(do_id=do_id).all()

    ccm_set = set(map(lambda x: x['dfo_id'], ccm_dfos))
    sim_set = set(map(lambda x: x.dfo_id, sim_dfos))

    # Need to delete DFOs
    for dfo_id in sim_set - ccm_set:
        # Through DB cascade, just delete DeviceFeatureObject.
        DeviceFeatureObject.objects.filter(dfo_id=dfo_id).delete()

    # Need to create DFOs
    create_set = ccm_set - sim_set
    if create_set:
        do_info = ccmapi(
            'deviceobject.get',
            {'p_id': p_id, 'do_id': do_id},
            u_id
        )

        for dfo_id in create_set:
            # Get create DFO info
            _info = list(filter(lambda x: x['dfo_id'] == dfo_id, ccm_dfos))[0]

            # Get DF_Parameters from ccm_do by check the same df_name
            # TOFIX: shouldn't use alias_name
            _info['df_parameters'] = list(filter(
                lambda x: x['df_name'] == _info['alias_name'],
                do_info['df_list']
            ))[0]['df_parameter']

            create_dfo(do_id, _info)
            # TODO: handle create fail.

    return True


def sync_dos(p_id, ccm_dos, u_id):
    # Sync DeviceObjects,
    sim_dos = DeviceObject.objects.filter(p_id=p_id).all()

    ccm_set = set(map(lambda x: x.get('do_id'), ccm_dos))
    sim_set = set(map(lambda x: x.do_id, sim_dos))

    # Need to delete DOs.
    for do_id in sim_set - ccm_set:
        # Through DB cascade, just delete DeviceObject.
        # TODO: check cascade
        DeviceObject.objects.filter(do_id=do_id).delete()

    # Need to sync DOs.
    for do_id in ccm_set & sim_set:
        # Get sync DO info
        do_info = list(filter(lambda x: x['do_id'] == do_id, ccm_dos))[0]

        DeviceObject.objects.filter(do_id=do_id).update(ccm_d_id=do_info.get('d_id'))
        sync_dfos(p_id, do_id, do_info['dfo'], u_id)
        # TODO: handle sync fail.

    # Need to create DOs.
    for do_id in ccm_set - sim_set:
        # Get create DO info
        do_info = list(filter(lambda x: x['do_id'] == do_id, ccm_dos))[0]

        create_do(p_id, do_info, u_id)
        # TODO: handle create fail.

    return True


def sync_project(p_id, u_id):
    # get CCM Project info.
    ccm_project = ccmapi('project.get', {'p_id': p_id}, u_id)

    # get SimTalk DB Project info.
    sim_project = Project.objects.filter(p_id=p_id).first()

    if sim_project is None:
        # No Porject data in DB, create it.
        return create_project(p_id, ccm_project, u_id)
    else:
        # Update p_name, if p_name can change in the future
        sim_project.p_name = ccm_project.get('p_name')
        sim_project.save()

        # Porject is existed in DB, sync DeviceObjects.
        return sync_dos(p_id, ccm_project['ido'], u_id)


def update_execution(p_id, u_id, do_infos):
    '''This function update the DO records, and stop the AG device.'''
    # Project.sim flag
    p_sim = SimStatus.OFF

    for do in do_infos:
        do_id = do.get('do_id')
        do_record = DeviceObject.objects.get(do_id=do_id)

        # If is had AG device, then shutdown first
        if do_record.ag_token:
            stop_simulator(do_record)

        # If sim='on', start simulator
        if do.get('sim') == SimStatus.ON:
            # Set Project.sim flag to 'on'
            p_sim = SimStatus.ON

            # Create simulator as AG Device
            do_record.ag_token = start_simulator(do_record)

        # Update DB record
        do_record.sim = do.get('sim')
        do_record.save()

    # Update the Project status
    update_ccm_simulation(p_id, u_id, p_sim)


def update_dfos(do_id, dfos):
    # Temporarily store objects to be updated
    update_list = []

    # Prepare DeviceObject, set is_default = False
    do_record = DeviceObject.objects.get(do_id=do_id)
    do_record.is_default = False
    update_list.append(do_record)

    # Prepare each DeviceFeatureObject update objects
    for dfo in dfos:
        dfo_id = dfo['dfo_id']
        vds = dfo['value_distributions']
        td = dfo['time_distribution']

        # Prepare DeviceFeatureObject, set is_default = False
        dfo = DeviceFeatureObject.objects.get(dfo_id=dfo_id)
        dfo.is_default = False
        update_list.append(dfo)

        # Prepare ValueDistribution update object
        for vd in vds:
            vd_record = ValueDistribution.objects.get(dfo_id=dfo_id, param_i=vd['param_i'])

            # Set mean, var, min, max by the param_type (int or float)
            for key in vd.keys() & {'mean', 'var', 'min', 'max'}:
                _type = getattr(builtins, vd['param_type'])
                setattr(vd_record, key, _type(vd[key]))

            # Set distribution, seed
            for key in vd.keys() & {'distribution', 'seed'}:
                setattr(vd_record, key, vd[key])

            update_list.append(vd_record)

        # Prepare TimeDistribution update object
        td_record = TimeDistribution.objects.get(dfo_id=dfo_id)
        td.pop('dfo_id')  # TOFIX
        for key, value in td.items():
            setattr(td_record, key, value)

        update_list.append(td_record)

    # Check data is clean
    ErrorMessage = []
    for obj in update_list:
        try:
            obj.full_clean()
        except ValidationError as e:
            m = {
                'name': obj._meta.model_name,
                'error': e.messages,
            }

            if m['name'] == 'valuedistribution':
                m['param_i'] = obj.param_i

            ErrorMessage.append(m)

    # Data is not clean, return msg
    if ErrorMessage:
        log.error('Error: %s', ErrorMessage)
        return ErrorMessage

    # Data is clean, save all update objects
    for obj in update_list:
        obj.save()

    return True
