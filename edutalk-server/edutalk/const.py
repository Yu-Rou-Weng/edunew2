import os
from edutalk.config import config

version = (2, 0, 0)

BASEDIR = os.path.abspath(os.path.dirname(__file__))

# this file define the options for sensors and actuators
# this file must be fixed after installation !!!
# we do not provide any guarantee if you modify this file after system setup
# todo: modify models.create_na to support adding new sensors/actuators after system setup

# all idf name must be unique before redesign of replay !!!
# the keys in first level is device
# the keys in second level is sensor
sensorOptions = {
    'Input Box': {
        'dimension': 1,
    },
    'Range Slider': {
        'dimension': 1,
    },
    'Smartphone': {
        'Acceleration': {
            'dimension': 3,
            'unit': 'm/s^2',
        },
        'Gyroscope': {
            'dimension': 3,
            'unit': 'rad/s',
        },
        'Orientation': {
            'dimension': 3,
            'unit': 'deg/s',
        },
        'Magnetometer': {
            'dimension': 3,
        },
    },
    'Morsensor': {
        # "Acceleration": {
        # "dimension": 3,
        # "unit": "m/s^2"
        # },
        # "Gyroscope": {
        # "dimension": 3,
        # "unit": "rad/s"
        # },
        # "Magnetometer": {
        # "dimension": 3,
        # },
        'Humidity': {
            'dimension': 1,
            'unit': '%',
        },
        # "Temperature": {
        # "dimension": 1,
        # "unit": "°C"
        # },
        'UV': {
            'dimension': 1,
        },
        'Alcohol': {
            'dimension': 1,
            'unit': '%',
        },
    },
    # unlike actuators, adding new sensor devices is expensive and should consider below issues:
    # 1. from now on, device must be the device model name in iottalk !!!
    # 2. from now on, idf name will be device+sensor+"-I" by default !!!
    # ex. "M2AtPressure-I"

    # 3. note if you are adding multidimensional sensors, you
    # should also modify card.html near v-model="settingIv.params[index].function
    # to let users to choose the index/function from new sensors

    # 4. note if you are adding new sensors before redesign replay/logger to frontend/variable based,
    # - you have to modify models.create_na and animation.js to support replay/logger
    # - you should send [idf name, data..., time] in your actual input device to follow the logger
    # rules, or you have to run something like relay_m2
    # - you have to create something like m2.py to deal with your device binding and called the binding
    # endpoints in order just like in animation.js and bind_callbacks in rc.py
    # because the order of binding in iottalk will affect join functions !!!
    'M2': {
        'AtPressure': {
            'dimension': 1,
        },
        'CO2': {
            'dimension': 1,
        },
        'Humidity1': {
            'dimension': 1,
            'unit': '%',
        },
        'Humidity2': {
            'dimension': 1,
            'unit': '%',
        },
        'Infrared': {
            'dimension': 1,
        },
        'Luminance': {
            'dimension': 1,
        },
        'Moisture': {
            'dimension': 1,
        },
        'PH1': {
            'dimension': 1,
        },
        'RainMeter': {
            'dimension': 1,
        },
        'SoilEC': {
            'dimension': 1,
        },
        'SoilTemp': {
            'dimension': 1,
        },
        'Temperature1': {
            'dimension': 1,
            'unit': '°C'
        },
        'Temperature2': {
            'dimension': 1,
            'unit': '°C'
        },
        'UV1': {
            'dimension': 1,
        },
        'WindDir': {
            'dimension': 1,
        },
        'WindSpeed': {
            'dimension': 1,
            'unit': 'm/s',
        },
    }}

# supported var type map by dim
actuatorVarTypeOfDim = {
    1: ['value'],  # dim = 1
    2: ['array'],  # dim = 2
    3: ['array', 'vector'],  # dim = 3
    4: ['array'],
    5: ['array'],
    6: ['array'],
    7: ['array'],
    8: ['array'],
    9: ['array'],
}

# supported actuator device models
# follow the below example to add new actuators
# todo: keep model name only and get other fields from iottalk ? but will take a lot of time ...
actuatorDm = {
    'Bulb': {
        'odfs': {
            'Luminance-O': {
                'dim': 1,
                'min': [0],
                'max': [100],
                'type': ['float'],
                'unit': ['None']
            },
            'Color-O': {
                'dim': 3,
                'min': [0, 0, 0],
                'max': [255, 255, 255],
                'type': ['float', 'float', 'float'],
                'unit': ['None', 'None', 'None']
            },
        }
    },
    'Dummy_Device': {
        'odfs': {
            'DummyControl-O': {
                'dim': 1,
                'min': [0],
                'max': [0],
                'type': ['float'],
                'unit': ['None']
            },
        }
    },
    'SwitchSet': {
        'odfs': {
            'Switch-O1': {
                'dim': 1,
                'min': [0],
                'max': [1],
                'type': ['int'],
                'unit': ['None']
            },
            'Switch-O2': {
                'dim': 1,
                'min': [0],
                'max': [1],
                'type': ['int'],
                'unit': ['None']
            }
        }
    }
}
