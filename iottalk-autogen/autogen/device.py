"""Device Handler."""
import logging
import pathlib
import sys

from multiprocessing import get_context

from django.http import HttpResponse

from iottalkpy.dai import module_to_sa

from .exceptions import raise_compilation_error
from .models import Device

sys.path.append(str(pathlib.Path(__file__).parent.absolute()) + '/dan_v1')

log = logging.getLogger('autogen.device')
log.setLevel(logging.DEBUG)


# TODO load_module_from_str in dai
class App(object):
    def __init__(self, d):
        self.__dict__ = d


class _DeviceHandler():
    def __init__(self):
        self._mp_context = get_context('forkserver')
        self._device_processes = {}

        # create device when server restart
        log.info('Restart devices...')
        try:
            devices = list(Device.objects.all())
        except Exception:
            log.info('Failed to get device...maybe the database is not initialized.')
        else:
            for d in devices:
                try:
                    log.debug(f'create device: {d.token}')
                    self.create_device(d)
                except Exception:
                    log.error(f'create failed... {d.token}')

    def create_device(self, device):
        # Check if the device prcess exists
        # If it exists, stop first, then create again
        if self._device_processes.get(device.token):
            self.delete_device(device)

        fn = getattr(self, '_create_v{}_device'.format(device.version), None)
        if fn:
            return fn(device)

        return HttpResponse("version not support", status=400)

    def delete_device(self, device):
        # Check if the device prcess exists
        proc = self._device_processes.pop(device.token, None)
        if proc:
            proc.terminate()

        return device.token

    def _create_v1_device(self, device):
        proc = self._mp_context.Process(target=self._v1_proc,
                                        args=(device.to_dict(),))
        proc.daemon = True
        proc.start()

        self._device_processes[device.token] = proc

        return device.token

    @staticmethod
    def _v1_proc(device):
        filename = '<sa:{}>'.format(device['token'])
        context = {}
        try:
            code = compile(device['code'], filename, mode='exec')
            exec(code, context)
        except Exception:
            raise_compilation_error()

    def _create_v2_device(self, device):
        try:
            # compile SA code
            context = {}
            exec(device.code, context)

            # run device via DAI
            proc = module_to_sa(App(context))
            proc.start()
        except Exception:
            raise_compilation_error()

        self._device_processes[device.token] = proc

        return device.token


devicehandler = _DeviceHandler()
