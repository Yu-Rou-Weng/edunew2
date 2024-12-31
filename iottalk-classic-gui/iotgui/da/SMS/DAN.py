import time

import csmapi

# example
profile = {
    'd_name': 'D1',
    'dm_name': 'MorSensor',
    'u_name': 'yb',
    'is_sim': False,
    'df_list': ['Acceleration', 'Temperature'],
}
mac_addr = 'C860008BD249'


def get_mac_addr():
    from uuid import getnode
    mac = getnode()
    mac = ''.join(("%012X" % mac)[i:i + 2] for i in range(0, 12, 2))
    return mac


def detect_local_ec():
    EASYCONNECT_HOST = None
    import socket
    UDP_IP = ''
    UDP_PORT = 17000
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((UDP_IP, UDP_PORT))
    while EASYCONNECT_HOST is None:
        print('Searching for the IoTtalk server...')
        data, addr = s.recvfrom(1024)
        if str(data.decode()) == 'easyconnect':
            EASYCONNECT_HOST = 'http://{}:9999'.format(addr[0])
            csmapi.ENDPOINT = EASYCONNECT_HOST
            # print('IoTtalk server = {}'.format(csmapi.ENDPOINT))


timestamp = {}
MAC = get_mac_addr()


def register_device(addr=MAC):
    if (csmapi.ENDPOINT is None):
        detect_local_ec()

    global MAC
    MAC = addr
    MAC = 'IoTtalk_SMS'

    global timestamp
    for i in profile['df_list']:
        timestamp[i] = ''

    print('IoTtalk Server = {}'.format(csmapi.ENDPOINT))
    if csmapi.create(MAC, profile):
        print('This device has successfully registered.')
        return True
    else:
        print('Registration failed.')
        return False


def device_registration_with_retry(IP=None):
    if IP is None:
        csmapi.ENDPOINT = 'http://' + IP + ':9999'
    success = False
    while not success:
        try:
            register_device()
            success = True
        except Exception as e:
            print('Attach failed: '),
            print(e)
        time.sleep(1)


def pull(FEATURE_NAME):
    global timestamp

    data = csmapi.pull(MAC, FEATURE_NAME)
    if data != []:
        if timestamp[FEATURE_NAME] == data[0][0]:
            return None
        timestamp[FEATURE_NAME] = data[0][0]
        if data[0][1] != []:
            return data[0][1]
        else:
            return None
    else:
        return None


def push(FEATURE_NAME, *data):
    return csmapi.push(MAC, FEATURE_NAME, list(data))
