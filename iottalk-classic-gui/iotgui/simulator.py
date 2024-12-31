#!/usr/bin/env python3
"""Simulator for iottalk2."""
import hashlib
import logging
import time

from random import getrandbits, randint, uniform
from threading import Lock, Thread
from uuid import UUID

from iottalkpy.dan import Client
from iotgui import config as iot_config
from iotgui.ccm.modules.utils import color_wrapper

log = logging.getLogger(color_wrapper("SIMULATOR", iot_config.LOG_COLOR_SIM))
log.setLevel(iot_config.LOG_LEVEL_SIM)

SIM_ALLOW_TYPE = set(['int', 'boolean', 'float'])


def sim_decorator(func):
    """
    Decorator.

    check simulator is online.
    """
    def wrap(s, *args):
        if s._dan:
            return func(s, *args)

    return wrap


class Simulator():
    """Simulator class for IoTtalk2 simulation."""

    def __init__(self, config, name=None):
        """
        Initial simulator with config.

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
        if not config.get('dm_name'):
            log.error("dm_name not find.")
            return

        if not config.get('do_id'):
            log.error("do_id not find.")
            return

        if not config.get('idf_list') and not config.get('odf_list'):
            log.error("idf_list/odf_list not find or empty.")
            return

        if name:
            self.name = name
        else:
            self.name = 'Sim-' + hex(getrandbits(16)).rstrip("L").lstrip("0x")

        for feature in config['idf_list']:
            if not config['idf_list'][feature].get('delay'):
                config['idf_list'][feature]['delay'] = 1

        self._config = config
        self._flags = {}
        self._threads = {}
        self._lock = Lock()
        self._is_alive = False
        self._do_id = config['do_id']

        idf_list = []
        for df_name in config['idf_list']:
            idf_list.append([df_name, config['idf_list'][df_name]['type']])
            self._flags[df_name] = False

        odf_list = []
        for df_name in config['odf_list']:
            odf_list.append([df_name, config['odf_list'][df_name]['type']])

        profile = {'model': config['dm_name'],
                   'is_sim': True,
                   'do_id': self._do_id}
        if 'u_name' in config:
            profile['u_name'] = config['u_name']

        self._dan = Client()
        self._context = self._dan.register(
            'http://{}:{}'.format(iot_config.MQTT.csm_host,
                                  iot_config.MQTT.csm_port),
            id_=str(UUID(hashlib.md5(str(self._do_id).encode()).hexdigest())),
            on_signal=self._on_signal,
            on_data=self._on_data,
            accept_protos=['mqtt'],
            name=self.name,
            profile=profile,
            idf_list=idf_list,
            odf_list=odf_list,
        )
        self._is_alive = False
        log.info("Simulator create, %s", self.name)

    def __del__(self):
        """Show destroy message."""
        log.info("Sim Destroy, %s", self.name)

    def _on_data(self, *argc):
        """Receive ODF data, ignored."""
        pass

    def _on_signal(self, signal, df_list):
        """Receive control signal."""
        log.info("Receive signal, %s: %s, df_list: %s",
                 self.name, signal, df_list)
        if 'CONNECT' == signal:
            for df_name in df_list:
                if df_name in self._flags:
                    self._start_generator(df_name)
        elif 'DISCONNECT' == signal:
            for df_name in df_list:
                self._stop_generator(df_name)
        elif 'SUSPEND' == signal:
            # Not use
            pass
        elif 'RESUME' == signal:
            # Not use
            pass

        return True

    def _generator(self, df_name, df_config):
        """Generate IDF data."""
        self._lock.acquire()
        if (not df_config['type']
           and set(df_config['type']).difference(SIM_ALLOW_TYPE)):

            self._lock.release()
            return
        self._lock.release()

        while (self._is_alive and self._flags.get(df_name)):
            data = []
            for type, min, max in zip(df_config['type'],
                                      df_config['min'],
                                      df_config['max']):
                if 'int' == type:
                    data.append(round(uniform(int(min), int(max))))
                elif 'float' == type:
                    data.append(uniform(float(min), float(max)))
                elif 'boolean' == type:
                    data.append(randint([True, False]))
                else:
                    data.append(None)

            self._dan.push(df_name, data)
            time.sleep(df_config['delay'])

    def _start_generator(self, df_name):
        self._flags[df_name] = True

        if not self._is_alive:
            return

        if not self._config['idf_list'].get(df_name):
            return

        if df_name in self._threads and self._threads[df_name].isAlive():
            self._stop_generator(df_name)

        self._lock.acquire()
        thread = Thread(target=self._generator,
                        args=(df_name, self._config['idf_list'][df_name]))
        thread.daemon = True
        thread.start()
        self._threads[df_name] = thread
        self._lock.release()

    def _stop_generator(self, df_name):
        self._lock.acquire()
        self._flags[df_name] = False

        if self._threads.get(df_name):
            while self._threads[df_name].isAlive():
                log.info("Wait %s thead stop.", df_name)
                time.sleep(1)
            del self._threads[df_name]

        self._lock.release()

    @sim_decorator
    def set_delay(self, df_name, delay):
        """
        Allow user modify features push delay time in config.

        :param df_name: which feature's delay need to modify.
        :param delay: the time interval between each data pushed.
        """
        self._config['idf_list'][df_name]['delay'] = delay
        if df_name in self._threads and self._threads[df_name].isAlive():
            self._start_generator(df_name)

    @sim_decorator
    def set_config(self, config):
        """
        Allow user modify config.

        :param config: check init.
        """
        for feature in config['idf_list']:
            if not ('delay' in config['idf_list'][feature]):
                config['idf_list'][feature]['delay'] = 1
        self._config = config

    @sim_decorator
    def set_df_config(self, df_name, config):
        """
        Allow user modify features config.

        :param df_name: which feature need to modify.
        :param config: new config for the feature.
            config = {
                `feature_name`: {
                    'delay': 1, # second, optional, default = 1
                    'type': [ 'int'/'boolean'/'float', ...],
                    'min': [ 0, ...],
                    'max': [ 100, ...],
                },
                ...
            }
        """
        self._config['idf_list'][df_name] = config
        if df_name in self._threads and self._threads[df_name].isAlive():
            self._start_generator(df_name)

    def is_alive(self):
        """Check this simulator still working."""
        return self._is_alive

    @sim_decorator
    def start(self):
        """Start this simulator."""
        if self._is_alive:
            log.info("Simulator started, %s", self.name)
        else:
            log.info("Simulator start, %s", self.name)
            self._is_alive = True
            for df_name in self._flags:
                if self._flags[df_name]:
                    self._start_generator(df_name)

    @sim_decorator
    def stop(self):
        """Stop this simulator."""
        log.info("Simulator stop, %s", self.name)
        self._is_alive = False

    @sim_decorator
    def deregister(self):
        """Stop this simulator."""
        log.info("Simulator deregister, %s", self.name)
        self.stop()
        self._dan.deregister()
