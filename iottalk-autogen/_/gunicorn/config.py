import os

import multiprocessing

from django.conf import settings


# This file contains gunicorn configurations.
#
# Ref: https://docs.gunicorn.org/en/stable/settings.html


# Access log format configurations
#
# Ref: https://docs.gunicorn.org/en/latest/settings.html#access-log-format
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s "%(f)s" "%(a)s"'

# Logging configurations dict
#
# Ref: https://docs.gunicorn.org/en/latest/settings.html#logconfig-dict
# Ref: https://tinyurl.com/2wnza346
logconfig_dict = {
    'version': 1,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'error_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': 'ext://sys.stderr',
        },
        'log_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(settings.LOG_DIR, 'gunicorn_access.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 3,
            'encoding': 'UTF-8',
        },
        'error_log_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(settings.LOG_DIR, 'gunicorn_error.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 3,
            'encoding': 'UTF-8',
        },
    },
    'loggers': {
        'gunicorn.access': {
            'handlers': [
                'console',
                'log_file',
            ],
            'level': 'INFO',
        },
        'gunicorn.error': {
            'handlers': [
                'error_console',
                'error_log_file',
            ],
            'level': 'INFO',
        },
    },
}

# Socket configurations
bind = '0.0.0.0:8080'

# Worker Processes
workers = 1
