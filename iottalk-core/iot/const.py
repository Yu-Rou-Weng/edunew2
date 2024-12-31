'''
Lots of constant vars here.
'''
import os

version = (2, 3, 0)

SRC_DIR = os.path.realpath(os.path.dirname(__file__))
BASE_DIR = os.path.realpath(os.path.join(SRC_DIR, '..'))
FIXTURES_DIR = os.path.join(BASE_DIR, 'fixtures')

# The feature mode denotes ``input``, ``output`` or both.
# http://iottalk-spec.rtfd.io/en/latest/protos/res_access_proto.html#metadata
FEATURE_MODE = ('i', 'o', 'io', 'oi')
