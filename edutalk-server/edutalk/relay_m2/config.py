import os

IoTtalkV1_url = os.getenv('IoTtalkV1_url', 'http://sdwan.iottalk.tw')
IoTtalkV2_url = os.getenv('IoTtalkV2_url', 'https://edutalk.joejoe2.com/iottalk/csm')
IoTtalkV1_dm_name = os.getenv('IoTtalkV1_dm_name', 'RelayM2')
IoTtalkV2_dm_name = os.getenv('IoTtalkV2_dm_name', 'M2')
IoTtalkV1_mac_addr = os.getenv('IoTtalkV1_mac_addr', 'C860008BD252')
IoTtalkV2_mac_addr = os.getenv('IoTtalkV2_mac_addr', '0d9d3522-d298-4367-820d-73c7a0df3511')

dname = os.getenv('dname', 'relay_m2')

device_v1_settings = {
    'IoTtalkURL': IoTtalkV1_url,
    'd_name': dname,
    'dm_name': IoTtalkV1_dm_name,
    'u_name': '',
    'is_sim': False,
    'Reg_addr': IoTtalkV1_mac_addr,
    'df_list': ['M2AtPressure-O', 'M2CO2-O', 'M2Humidity1-O', 'M2Humidity2-O', 'M2Infrared-O', 'M2Luminance-O',
                'M2Moisture-O', 'M2PH1-O', 'M2RainMeter-O', 'M2SoilEC-O', 'M2SoilTemp-O', 'M2Temperature1-O',
                'M2Temperature2-O', 'M2UV1-O', 'M2WindDir-O', 'M2WindSpeed-O'],
    'idf_list': [],
    'odf_list': ['M2AtPressure-O', 'M2CO2-O', 'M2Humidity1-O', 'M2Humidity2-O', 'M2Infrared-O', 'M2Luminance-O',
                 'M2Moisture-O', 'M2PH1-O', 'M2RainMeter-O', 'M2SoilEC-O', 'M2SoilTemp-O', 'M2Temperature1-O',
                 'M2Temperature2-O', 'M2UV1-O', 'M2WindDir-O', 'M2WindSpeed-O']
}

device_v2_settings = {
    'IoTtalkURL': IoTtalkV2_url,
    "idf_list": [
        ('M2AtPressure-I', ['']),
        ('M2CO2-I', ['']),
        ('M2Humidity1-I', ['']),
        ('M2Humidity2-I', ['']),
        ('M2Infrared-I', ['']),
        ('M2Luminance-I', ['']),
        ('M2Moisture-I', ['']),
        ('M2PH1-I', ['']),
        ('M2RainMeter-I', ['']),
        ('M2SoilEC-I', ['']),
        ('M2SoilTemp-I', ['']),
        ('M2Temperature1-I', ['']),
        ('M2Temperature2-I', ['']),
        ('M2UV1-I', ['']),
        ('M2WindDir-I', ['']),
        ('M2WindSpeed-I', [''])
    ],
    "odf_list": [],
    "name": dname,
    "profile": {
        'model': IoTtalkV2_dm_name,
    },
    "Reg_addr": IoTtalkV2_mac_addr
}
