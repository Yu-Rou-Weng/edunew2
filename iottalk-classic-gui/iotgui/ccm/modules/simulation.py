"""
Simulation module.

contains:

    op_turn_on_simulation
    op_turn_off_simulation
    op_get_simulation_status

    create_simulator
    delete_simulator

_sim_proc
"""
import gc
import logging
import multiprocessing

from sqlalchemy import and_

from iotgui import config
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError
from iotgui.db import model

log = logging.getLogger("{}SIM\033[0m".format(config.LOG_COLOR_SIM))
log.setLevel(config.LOG_LEVEL_SIM)


class Simulation(Interface):
    """Simulation class."""

    _simulator = {}  # Key: do_id, Value: Simulator instance

    def op_update_simulation(self, ctx, p_id, sim):
        """
        Update Project's simulation status.

        Note: This API only for simtalk use, and only update the DB.

        :param p_id: <Project.p_id>
        :param sim: 'on' / 'off'
        :type p_id: int
        :type sim: str

        :return:
            {
                'p_id': '<Project.p_id>',
                'sim': 'on' / 'off'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check project exist
        project_record = self._query_project(db_session, u_id, p_id)
        if not project_record:
            raise CCMError('project id {} not found'.format(p_id))

        pre_sim = project_record.sim
        if str(pre_sim) == str(sim):
            return {'sim': sim, 'p_id': p_id}

        # update Project simulation status
        (db_session.query(model.Project)
                   .filter(and_(model.Project.p_id == p_id,
                                model.Project.u_id == u_id))
                   .update({'sim': sim}))
        db_session.commit()

        return {'sim': sim, 'p_id': p_id}

    def op_turn_on_simulation(self, ctx, p_id):
        """
        Change the Project's simulation status to 'on'.

        Server will automatically create the simulators
        for each input Device Object in the Project with given p_id.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            'on'
        """
        db_session = ctx.db_session

        # update project's simulation status
        (db_session
            .query(model.Project)
            .filter(model.Project.p_id == p_id)
            .update({'sim': 'on'}))
        db_session.commit()

        if not config.SIMTALK_ENDPOINT:
            # No SimTalk, use basic simulation
            # create simulator for all device object
            do_records = (db_session.query(model.DeviceObject)
                                    .filter(model.DeviceObject.p_id == p_id)
                                    .all())

            for do_record in do_records:
                # check simulator exist
                if str(do_record.do_id) not in self._simulator:
                    self.create_simulator(ctx, do_record.do_id)

        return 'on'

    def op_turn_off_simulation(self, ctx, p_id):
        """
        Change the Project's simulation status to 'off'.

        Server will destroy all simulators in the Project with given p_id.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            'off'
        """
        db_session = ctx.db_session

        # update project's simulation status
        (db_session
            .query(model.Project)
            .filter(model.Project.p_id == p_id)
            .update({'sim': 'off'}))
        db_session.commit()

        if not config.SIMTALK_ENDPOINT:
            # No SimTalk, use basic simulation
            # remove all simulator for all device object
            do_records = (db_session.query(model.DeviceObject)
                                    .filter(model.DeviceObject.p_id == p_id)
                                    .all())

            for do_record in do_records:
                self.delete_simulator(ctx, do_record.do_id)

        return 'off'

    def op_get_simulation_status(self, ctx, p_id):
        """
        Get the Project's simulation situation.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            'on' / 'off'
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check project exist
        project_record = (db_session.query(model.Project)
                                    .filter(and_(model.Project.p_id == p_id,
                                                 model.Project.u_id == u_id))
                                    .first())
        if not project_record:
            raise CCMError('Project not find. u_id:{}, p_id:{}.'.format(u_id, p_id))

        return project_record.sim

    def create_simulator(self, ctx, do_id):
        """
        Create Simulator instance.

        :param do_id:
            <DeviceObject.do_id>

        :return:
            True / False
        """
        db_session = ctx.db_session

        # check simulator is exist
        if str(do_id) in self._simulator:
            return True

        simulator_config = {
            'dm_name': '',
            'do_id': do_id,
            'idf_list': {},
            'odf_list': {},
        }

        if ctx.u_id:
            user_record = (db_session.query(model.User)
                                     .filter(model.User.u_id == ctx.u_id)
                                     .first())
            if user_record:
                simulator_config['u_name'] = user_record.u_name

        # get DeviceModel info
        dm_record = (db_session.query(model.DeviceModel)
                               .select_from(model.DeviceObject)
                               .join(model.DeviceModel)
                               .filter(model.DeviceObject.do_id == do_id)
                               .first())
        if not dm_record:
            return False

        dm_id = dm_record.dm_id
        simulator_config['dm_name'] = dm_record.dm_name

        # get DeviceFeature info
        df_records = (db_session.query(model.DeviceFeature)
                                .select_from(model.DM_DF)
                                .join(model.DeviceFeature)
                                .filter(model.DM_DF.dm_id == dm_id)
                                .all())

        if not df_records:
            return False

        for df_record in df_records:
            df_type = 'idf_list' if (df_record.df_type == 'input') else 'odf_list'

            # get DF_Parameter info
            dfps = self.op_get_device_feature_parameter(
                ctx, df_id=df_record.df_id, dm_id=dm_id).get('df_parameter', [])

            df_temp = {
                'type': [],
                'min': [],
                'max': []
            }

            for dfp in dfps:
                df_temp['type'].append(dfp.get('param_type', 'int'))
                df_temp['min'].append(dfp.get('min', 0))
                df_temp['max'].append(dfp.get('max', 0))

            simulator_config[df_type][df_record.df_name] = df_temp.copy()

        # Create Simulator
        try:  # FIXME: simulation is buggy ATM.
            ctx = multiprocessing.get_context('forkserver')
            self._simulator[str(do_id)] = ctx.Process(target=_sim_proc,
                                                      args=(simulator_config,))
            self._simulator[str(do_id)].daemon = True
            self._simulator[str(do_id)].start()
        except Exception as e:
            log.error("create_simulator failed: %s", e)
            return False

        return True

    def delete_simulator(self, ctx, do_id):
        """
        Remove Simulator instance.

        :param do_id:
            <DeviceObject.do_id>

        :return:
            True / False
        """
        do_id = str(do_id)
        if do_id in self._simulator:
            if self._simulator[do_id].is_alive():
                self._simulator[do_id].terminate()
                self._simulator[do_id].join()
            # FIXME: del not work well
            del self._simulator[do_id]
            gc.collect()

        return True


def _sim_proc(config, name=None):
    """
    Run simulator in the process.

    Usage:
        >>> from multiprocessing import Process
        >>> p = Process(target=_sim_proc, args=(config, name))
        >>> p.start()

    :param config: This simulator config,
        config = {
            'dm_name': 'dm_name',
            'do_id': 'do_id',
            'idf_list': {
                `feature_name`: {
                    'delay': 1, # second, optional, default = 1
                    'type': [ 'int'/'boolean'/'float', ...],
                    'min': [ 0, ...],
                    'max': [ 100, ...],
                },
                ...
            }

        }
    :param name: optional, this simulator name
    """
    import signal

    from threading import Lock

    from iotgui.simulator import Simulator as Sim
    lock = Lock()  # for terminate process
    lock.acquire()

    sim = Sim(config, name)
    sim.start()

    def sig_handle(sig, frame):
        sim.deregister()
        lock.release()

    signal.signal(signal.SIGTERM, sig_handle)

    try:
        signal.pause()
    except Exception:
        lock.acquire()  # wait to deregister
