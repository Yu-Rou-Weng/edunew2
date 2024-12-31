import logging
import re

from edutalk.config import config
from edutalk.utils import ag_ccmapi, CCMAPIError
from edutalk.const import actuatorVarTypeOfDim, actuatorDm

db = config.db
log = logging.getLogger('edutalk.actuator')


def check_output_variables(output_variables: dict, cyber_var_names={}):
    var_names = {}
    for actuator_var in output_variables:
        for field in ('name', 'type', 'default', 'actuator', 'odf', 'mac_addr'):
            if field not in actuator_var:
                return 'field {} is missing'.format(field)

        if actuator_var['name'] in var_names or actuator_var['name'] in cyber_var_names:
            return 'actuator variable {} is repeated'.format(actuator_var['name'])
        else:
            var_names[actuator_var['name']] = actuator_var['name']

        if not actuator_var['name']:
            return 'name of actuator variable cannot be empty'

        if type(actuator_var['name']) != str or not actuator_var['name'].isidentifier():
            return 'name of actuator variable {} is invalid, ' \
                   'english alphabet or number or _ only'.format(actuator_var['name'])

        if actuator_var['dim'] != len(actuator_var['default']):
            return 'length of default should be same with dimension'

        for value in actuator_var['default']:
            if type(value) == str and (value.find("'", 1, len(value) - 1) != -1
                                       or '"' in value or "\\" in value):
                return 'default should not contain \', \", or \\ '

        if actuator_var['dim'] not in actuatorVarTypeOfDim:
            return 'dimensions cannot be {}.'.format(actuator_var['dim'])

        if actuator_var['type'] not in actuatorVarTypeOfDim[actuator_var['dim']]:
            return 'type of actuator variable {} can only be one of {}'. \
                format(actuator_var['name'], actuatorVarTypeOfDim[actuator_var['dim']])

        if actuator_var['actuator'] and actuator_var['actuator'] not in actuatorDm:
            return 'actuator can only be one of '.format(actuatorDm)

        if actuator_var['actuator'] and not actuator_var['odf']:
            return 'actuator variable {} must select one odf'.format(actuator_var['name'])

        if actuator_var['actuator'] and actuator_var['odf'] \
                not in actuatorDm[actuator_var['actuator']]['odfs']:
            return 'odf {} is not exist'.format(actuator_var['odf'])

        if actuator_var['mac_addr'] and not actuator_var['actuator']:
            return 'actuator variable {} is missing actuator and odf'.format(actuator_var['name'])

    return ''


def create_actuator_dfs(u_id, lec_name, output_variables):
    """
create device features for selected actuator vars(lec_name + actuator_var['name'])
and return (name of created dfs, processed output_variables)

    @param u_id: user id
    @param lec_name: name of lecture
    @param output_variables: in format of
            [
                  {
                    'key': var key for count,
                    'name': name of variable
                    'type': type of variable,
                    'dim': number of dimensions
                    'default': [...],
                    'actuator': dm name of actuator, # can be empty
                    'odf': odf name of actuator, # can be empty
                    'mac_addr': mac addr of actuator da, # can be empty
                  }, ...
            ]
    @return: (list, list)
    """
    dfs, vars = [], []

    for actuator_var in output_variables:
        df = {'df_name': lec_name + actuator_var['name'] + '-I',
              'type': 'input',
              'parameter': []
              }
        for _ in range(0, len(actuator_var['default'])):
            df['parameter'].append(
                {'param_type': 'float',
                 'min': 0,
                 'max': 0
                 }
            )

        try:
            ag_ccmapi(u_id, 'devicefeature.get', {'key': df['df_name']})
        except CCMAPIError:
            ag_ccmapi(u_id, 'devicefeature.create', df)
        finally:
            dfs.append(df['df_name'])
            vars.append({
                'name': actuator_var['name'],
                'type': actuator_var['type'],
                'dim': actuator_var['dim'],
                'default': actuator_var['default'],
                'idf': [df['df_name'], [''] * len(df['parameter'])],
                'actuator': '',  # dm of actuator
                'odf': '',  # odf of actuator
                'mac_addr': '',  # mac_addr of actuator
                'params': [{'model': '', 'mac_addr': '', 'odf': '', 'pos': 0}] * actuator_var['dim'],
            })

    return dfs, vars


def prepare_idfs(u_id, dim, count):
    idfs = []
    for i in range(1, count + 1):
        df = {'df_name': 'Dim{0}-I{1}'.format(dim, i),
              'type': 'input',
              'parameter': []
              }
        for _ in range(0, dim):
            df['parameter'].append(
                {'param_type': 'float',
                 'min': 0,
                 'max': 0
                 }
            )
        try:
            ag_ccmapi(u_id, 'devicefeature.get', {'key': df['df_name']})
        except CCMAPIError:
            ag_ccmapi(u_id, 'devicefeature.create', df)
        finally:
            idfs.append(df['df_name'])
    return idfs
