import time
import requests
import csmapi

while True:
    try:
        profile = {
            'd_name': 'Message',
            'dm_name': 'Message',
            'u_name': 'yb',
            'is_sim': False,
            'df_list': [],
        }
        for i in range(1, 10):
            profile['df_list'].append("Name%d" % i)
        result = csmapi.register('IoTtalk_Message', profile)
        if result:
            break
    except requests.exceptions.ConnectionError as e:
        print('requests.exceptions.ConnectionError:', e)
        print('retry after 3 second')
        time.sleep(3)
    except csmapi.CSMError as e:
        print('csmapi.CSMError:', e)
        print('retry after 3 second')
        time.sleep(3)

print('Message registraion is done.')
