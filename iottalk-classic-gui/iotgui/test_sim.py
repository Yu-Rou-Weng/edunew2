import iotgui.ccm.simulator


def test():
    c = {
        'dm_name': 'Remote_control',
        'idf_list': {
            'Keypad1': {
                'type': ['int'],
                'min': [0],
                'max': [9]
            }
        }
    }
    return iotgui.ccm.simulator.Simulator(c)
