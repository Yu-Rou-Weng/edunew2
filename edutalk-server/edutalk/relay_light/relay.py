import queue
import sys

from iottalkpy import dan as dan2
import DAN as dan1
import time
import threading
import config


class DeviceApplicationv2():
    def __init__(self, device_v2_settings):
        self.deviceSettings = device_v2_settings
        self.client = dan2.Client()
        self._proc = threading.Thread(target=self._run)
        self.queue = queue.Queue()

    def start(self):
        self._proc.start()

    def stop(self):
        self.client.deregister()
        self._proc.terminate()
        self._proc.join()

    def push_data(self, df_name, data):
        print("[push]", df_name, " ", data)
        self.client.push(df_name, data)
        return

    def on_data(self, *args):
        self.queue.put_nowait(args)
        return True

    def pull_data(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

    def on_signal(self, signal, df_list):
        print(signal, ": ", df_list)
        if 'CONNECT' == signal:
            for df_name in df_list:
                pass
        elif 'DISCONNECT' == signal:
            pass
        elif 'SUSPEND' == signal:
            # Not use
            pass
        elif 'RESUME' == signal:
            # Not use
            pass
        return True

    def on_register(self, dan):
        print("v2 register successfully")

    def _run(self):
        self.client.register(
            self.deviceSettings['IoTtalkURL'],
            on_signal=self.on_signal,
            on_data=self.on_data,
            idf_list=self.deviceSettings['idf_list'],
            odf_list=self.deviceSettings['odf_list'],
            name=self.deviceSettings['name'],
            profile=self.deviceSettings['profile'],
            accept_protos=['mqtt'],
            on_register=self.on_register,
            id_=self.deviceSettings['Reg_addr']
        )
        # self.client.loop_forever()


class DeviceApplicationv1():
    def __init__(self, device_v1_settings):
        self.deviceSettings = device_v1_settings
        self.value = {}
        self._proc = threading.Thread(target=self._run)

    def start(self):
        self._proc.daemon = True
        self._proc.start()

    def stop(self):
        dan1.deregister()
        self._proc.terminate()
        self._proc.join()

    def push_data(self, df_name, data):
        print("[push]", df_name, " ", data)
        dan1.push(df_name, *data)
        return

    def pull_data(self):
        return self.value

    def _run(self):
        dan1.profile['dm_name'] = self.deviceSettings['dm_name']
        dan1.profile['df_list'] = self.deviceSettings['df_list']
        dan1.profile['d_name'] = self.deviceSettings['d_name']  # None for autoNaming
        dan1.device_registration_with_retry(self.deviceSettings['IoTtalkURL'], self.deviceSettings['Reg_addr'])

        while True:
            try:
                for df in self.deviceSettings['odf_list']:
                    pull_value = dan1.pull(df)
                    if pull_value != None:
                        self.value.update({df: pull_value[0]})
            except Exception as e:
                print(e)
                if str(e).find('mac_addr not found:') != -1:
                    print('Reg_addr is not found. Try to re-register...')
                    dan1.device_registration_with_retry(self.deviceSettings['IoTtalkURL'],
                                                        self.deviceSettings['Reg_addr'])
                else:
                    print('Connection failed due to unknow reasons.')
                    time.sleep(1)

            time.sleep(1)


class Relay():
    def __init__(self, config):
        self.v1_DA = DeviceApplicationv1(config.device_v1_settings)
        self.v2_DA = DeviceApplicationv2(config.device_v2_settings)
        self.v1_DA.start()
        self.v2_DA.start()
        self._proc = threading.Thread(target=self._run)

    def start(self):
        self._proc.daemon = True
        self._proc.start()

    def stop(self):
        self.v1_DA.stop()
        self.v2_DA.stop()
        self._proc.terminate()
        self._proc.join()

    def _run(self):
        while True:
            try:
                value = self.v2_DA.pull_data()
                if value:
                    df = value[0].replace("-O", "")
                    data = value[1]
                    self.v1_DA.push_data(df, data)
                    continue
            except Exception as e:
                print(e)
            except KeyboardInterrupt:
                self.v1_DA.stop()
                self.v2_DA.stop()
                sys.exit()

            time.sleep(0.1)


if __name__ == '__main__':
    relay = Relay(config)
    relay.start()
    while True:
        time.sleep(0.1)
