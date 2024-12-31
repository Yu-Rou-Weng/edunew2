import os

from setuptools import find_packages, setup

import _

BASE_DIR = os.path.dirname(__file__)


def get_requires():
    with open(os.path.join(BASE_DIR, 'requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines())) + get_backport_requires()


def get_backport_requires():
    return tuple()


setup(
    name='iottalkautogen',
    version=_.version,
    author='The IoTtalk Team',
    author_email='IoTtalkcontributors',
    url='https://github.com/IoTtalk/AutoGen-Subsystem',
    packages=find_packages(exclude=['tests']),
    install_requires=get_requires(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
