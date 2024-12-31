import os

IoTtalkV1_url = os.getenv('IoTtalkV1_url', 'https://iot.iottalk.tw/')
IoTtalkV2_url = os.getenv('IoTtalkV2_url', 'https://edutalk.joejoe2.com/iottalk/csm')
IoTtalkV1_dm_name = os.getenv('IoTtalkV1_dm_name', 'Remote_control')
IoTtalkV2_dm_name = os.getenv('IoTtalkV2_dm_name', 'SwitchSet')
IoTtalkV1_mac_addr = os.getenv('IoTtalkV1_mac_addr', 'C861008BD610')
IoTtalkV2_mac_addr = os.getenv('IoTtalkV2_mac_addr', '0d9d3522-d298-4367-820d-63c7a0df35ff')

dname = os.getenv('dname', '610SwitchSet')

device_v1_settings = {
    'IoTtalkURL': IoTtalkV1_url,
    'd_name': dname,
    'dm_name': IoTtalkV1_dm_name,
    'u_name': '',
    'is_sim': False,
    'Reg_addr': IoTtalkV1_mac_addr,
    'df_list': ['Switch1', 'Switch2'],
    'idf_list': [
        ('Switch1', ['']),
        ('Switch2', [''])
    ],
    'odf_list': []
}

device_v2_settings = {
    'IoTtalkURL': IoTtalkV2_url,
    "idf_list": [],
    "odf_list": [
        ('Switch-O1', ['']),
        ('Switch-O2', [''])
    ],
    "name": dname,
    "profile": {
        'model': IoTtalkV2_dm_name,
    },
    "Reg_addr": IoTtalkV2_mac_addr
}
