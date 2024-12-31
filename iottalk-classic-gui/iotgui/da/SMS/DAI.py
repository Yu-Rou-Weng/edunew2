import json
import os
import subprocess
import time

import requests

import DAN

# SMS Setting #
SMS_SERVER_IP = '202.39.54.130'
SMS_SERVER_LOGIN = '89945934'
SMS_SERVER_PWD = '46804706'


def send_SMS(msg, tel):
    current_path = os.path.dirname(__file__)
    # print (current_path)
    # print (os.path.join(current_path, os.path.join('SMS')))

    subprocess.Popen([
        os.path.join(current_path, os.path.join('SMS')),
        SMS_SERVER_IP,
        SMS_SERVER_LOGIN,
        SMS_SERVER_PWD,
        tel,
        msg
    ])


DAN.profile['dm_name'] = 'SMS'
DAN.profile['d_name'] = 'SMS_sender'
DAN.profile['df_list'] = ['SMS_content']

DAN.device_registration_with_retry('127.0.0.1')  # Connect to assign IP
# DAN.device_registration_with_retry()  # Auto Connect to the local IoTtalk server

while True:
    try:
        # Pull data from a device feature called "Dummy_Control"
        SMS = DAN.pull('SMS_content')
        if SMS is not None:
            if SMS[0] is not None:
                print('SMS text: ', json.loads(SMS[0])['text'])
                print('Phone num: ', json.loads(SMS[0])['phone'])
                send_SMS(str(json.loads(SMS[0])['text']), str(json.loads(SMS[0])['phone']))

    except requests.exceptions.ConnectionError:
        print("requests.exceptions.ConnectionError")
        DAN.device_registration_with_retry('127.0.0.1')

    time.sleep(0.5)
