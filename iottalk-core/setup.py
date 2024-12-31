import os
import sys

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

import iot

BASE_DIR = os.path.dirname(__file__)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


def get_requires():
    with open(os.path.join(BASE_DIR, 'requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines())) + get_backport_requires()


def get_backport_requires():
    return tuple()


def get_test_requires():
    with open(os.path.join(BASE_DIR, 'test-requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines()))


setup(
    name='iottalk',
    version=iot.version,
    author='IoTtalk',
    author_email='IoTtalkcontributors',
    maintainer='Iblis Lin, Chang-Yen Chih',
    maintainer_email=('iblis@hs.ntnu.edu.tw, '
                      'michael66230@gmail.com'),
    url='https://github.com/IoTtalk/iottalk-core',
    packages=find_packages(exclude=['tests']),
    data_files=[
        ('share/iottalk', ['share/iottalk.ini.sample']),
        ('', ['requirements.txt', 'test-requirements.txt']),
    ],
    entry_points={
        'console_scripts': ('iotctl=iot.cli:main',),
    },
    install_requires=get_requires(),
    tests_require=get_test_requires(),
    cmdclass={'test': PyTest},
    platforms=['FreeBSD'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
