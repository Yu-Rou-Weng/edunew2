import logging
import pytz
from datetime import datetime
from fluent import sender
from edutalk.config import config

log = logging.getLogger('edutalk.simple_logger')

api_url = config.csm_api
device_name = 'Logger'
device_model = 'SimpleLogger'

device_addr = "8d7fa1cf-0c3e-45fa-b936-1a7aad119874"

odf_list = ['EduAcc-O', 'EduGyr-O', 'EduMag-O', 'EduOri-O',
            'EduAlc-O', 'EduHum-O', 'EduUV-O', 'OneDimLogger-O']

timezone = pytz.timezone('Asia/Taipei')


def on_register(dan):
    global logger
    logger = sender.FluentSender('fluentd.edutalk', host='fluentd', port=24224)
    log.info('[dai] register successfully')


def on_deregister(dan):
    log.info('[da] deregister')


def EduAcc_O(data):
    timestamp = datetime.fromtimestamp(data[3] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduAcc_I',
        'sample': [data[0], data[1], data[2]],
    })


def EduGyr_O(data):
    timestamp = datetime.fromtimestamp(data[3] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduGyr_I',
        'sample': [data[0], data[1], data[2]],
    })


def EduMag_O(data):
    timestamp = datetime.fromtimestamp(data[3] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduMag_I',
        'sample': [data[0], data[1], data[2]],
    })


def EduOri_O(data):
    timestamp = datetime.fromtimestamp(data[3] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduOri_I',
        'sample': [data[0], data[1], data[2]],
    })


def EduAlc_O(data):
    timestamp = datetime.fromtimestamp(data[1] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduAlc_I',
        'sample': data[0],
    })


def EduHum_O(data):
    timestamp = datetime.fromtimestamp(data[1] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduHum_I',
        'sample': data[0],
    })


def EduUV_O(data):
    timestamp = datetime.fromtimestamp(data[1] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': 'EduUV_I',
        'sample': data[0],
    })


def OneDimLogger_O(data):
    timestamp = datetime.fromtimestamp(data[1] / 1000, timezone).isoformat()
    logger.emit('simple_logger', {
        'timestamp': timestamp,
        'from': data[2],
        'sample': data[0],
    })
