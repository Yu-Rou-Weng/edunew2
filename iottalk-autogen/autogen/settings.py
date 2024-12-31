import os

from dotenv import load_dotenv

from .settings import *  # noqa: F401,F403 imported but unused,import shared settings, F401

# Load the env to the environment variables
load_dotenv(os.path.join(BASE_DIR, '_/env/env'))

ROOT_URLCONF = 'autogen.urls'

INSTALLED_APPS += []

MIDDLEWARE += [
    'autogen.middleware.JsonRequestMiddleware',
]

CCM_API_URL = os.getenv('CCM_API_URL')

CCM_API_ARGS = {
    'account.create': {
        'required': {
            'username': str,
            'password': str,
        },
    },
    'account.login': {
        'required': {
            'username': str,
            'password': str,
        },
    },
    'account.oauth2': {
        'required': {
            'access_token': str,
        },
    },
    'account.delete': {},
    'account.profile': {},
    'devicefeature.create': {
        'required': {
            'df_name': str,
            'type': str,
            'parameter': list,
        },
        'optional': {
            'comment': str,
            'category': str,
        },
    },
    'devicefeature.get': {
        'optional': {
            'key': (str, int),
        },
    },
    'devicefeature.update': {
        'required': {
            'df_id': int,
            'df_name': str,
            'type': str,
            'parameter': list,
        },
        'optional': {
            'comment': str,
            'category': str,
        },
    },
    'devicefeature.delete': {
        'required': {
            'df': (str, int),
        },
    },
    'devicemodel.create': {
        'required': {
            'dm_name': str,
            'dfs': list,
        },
    },
    'devicemodel.get': {
        'optional': {
            'key': (str, int),
        },
    },
    'devicemodel.update': {
        'required': {
            'dm_id': int,
            'dm_name': str,
            'dfs': list,
        },
    },
    'devicemodel.delete': {
        'required': {
            'dm': (str, int),
        },
    },
    'project.create': {
        'required': {
            'p_name': str,
        },
    },
    'project.get': {
        'optional': {
            'key': (str, int),
        },
    },
    'project.delete': {
        'required': {
            'p_id': int,
        },
    },
    'project.on': {
        'required': {
            'p_id': int,
        },
    },
    'project.off': {
        'required': {
            'p_id': int,
        },
    },
    'simulation.get': {
        'required': {
            'p_id': int,
        },
    },
    'simulation.on': {
        'required': {
            'p_id': int,
        },
    },
    'simulation.off': {
        'required': {
            'p_id': int,
        },
    },
    'deviceobject.create': {
        'required': {
            'p_id': int,
            'dm_name': str,
        },
        'optional': {
            'dfs': list,
        },
    },
    'deviceobject.get': {
        'required': {
            'p_id': int,
            'do_id': int,
        },
    },
    'deviceobject.delete': {
        'required': {
            'p_id': int,
            'do_id': int,
        },
    },
    'devicefeatureobject.get': {
        'required': {
            'p_id': int,
            'do_id': int,
            'dfo_id': int,
        },
    },
    'devicefeatureobject.update': {
        'required': {
            'p_id': int,
            'do_id': int,
            'dfo_id': int,
            'alias_name': str,
            'df_parameter': list,
        },
    },
    'function.create': {
        'required': {
            'fn_name': str,
            'code': str,
        },
        'optional': {
            'df_id': int,
        }
    },
    'function.update': {
        'required': {
            'fn_id': int,
            'code': str,
        },
        'optional': {
            'df_id': int,
            'fnvt_idx': int,
        },
    },
    'function.delete': {
        'required': {
            'fn_id': int,
        },
    },
    'function.list': {},
    'function.list_df': {
        'required': {
            'df_id': int,
        },
    },
    'function.list_na': {},
    'function.get': {
        'required': {
            'fn_id': int,
        },
    },
    'function.get_all_versions': {
        'required': {
            'fn_id': int,
        },
    },
    'function.get_version': {
        'required': {
            'fnvt_idx': int,
        },
    },
    'function.create_sdf': {
        'required': {
            'fn_id': int,
        },
        'optional': {
            'df_id': int,
        },
    },
    'function.delete_sdf': {
        'required': {
            'fn_id': int,
        },
        'optional': {
            'df_id': int,
        },
    },
    'networkapplication.create': {
        'required': {
            'p_id': int,
            'joins': list,
        },
    },
    'networkapplication.get': {
        'required': {
            'p_id': int,
            'na_id': int,
        },
    },
    'networkapplication.update': {
        'required': {
            'p_id': int,
            'na_id': int,
            'dfm_list': list,
        },
        'optional': {
            'na_name': str,
            'multiplejoin_fn_id': int,
        },
    },
    'networkapplication.delete': {
        'required': {
            'p_id': int,
            'na_id': int,
        },
    },
    'device.get': {
        'required': {
            'p_id': int,
            'do_id': int,
        },
    },
    'device.bind': {
        'required': {
            'p_id': int,
            'do_id': int,
            'd_id': (int, str),
        },
    },
    'device.unbind': {
        'required': {
            'p_id': int,
            'do_id': int,
        },
    },
    'alias.get': {
        'required': {
            'mac_addr': str,
            'df_name': str,
        },
    },
    'alias.set': {
        'required': {
            'mac_addr': str,
            'df_name': str,
            'alias_name': str,
        },
    }
}

LOG_DIR =  os.path.join(LOG_DIR, 'autogen/')

# configure ccm api in global
#
import ccmapi.v0 as ccmapi

ccmapi.config.config.api_url = CCM_API_URL

