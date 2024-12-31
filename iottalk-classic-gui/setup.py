import itertools

from os import path, walk

from pathlib import Path
from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand

from iotgui import config

src_dir = str(Path(__file__).absolute().parent)


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
        import sys

        import pytest

        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


def get_requires():
    with open(path.join(src_dir, 'requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines()))


def get_test_requires():
    with open(path.join(src_dir, 'test-requirements.txt')) as f:
        return tuple(map(str.strip, f.readlines()))


def get_static_data():
    includes = []
    for dic in walk(path.join(src_dir, 'iotgui')):
        dic_name = dic[0]

        if dic_name.find('__pycache__') != -1:
            # skip __pycache__
            continue

        includes.append(path.join(dic_name, '*')[7:])

    return includes


def get_alembic_data():
    include_files = []
    alembic_directory = Path(src_dir) / 'iotgui/alembic'

    for file_path in alembic_directory.rglob('*'):
        if str(file_path).find('__pycache__') != -1:
            continue

        # Get the file path relative to src_dir/iotgui
        include_files.append(str(file_path.relative_to('{}/{}'.format(src_dir, 'iotgui'))))

    return include_files


setup(
    name='iottalk-gui',
    version=config.VERSION,
    description='Classic GUI for IoTtalk2.',
    keywords='python iot iottalk iottalk2 ccm gui',
    author='IoTtalk',
    author_email='IoTtalkcontributors',
    maintainer='Ksoy Yen',
    maintainer_email=('ksoyam95@gmail.com'),
    url='https://gitlab.com/iottalk/iottalk-classic-gui',
    license='MIT',
    packages=find_packages(),
    package_data={
        'iotgui': list(itertools.chain(get_alembic_data()))
    },
    data_files=[
        ('share/iottalk', ['share/iottalk-gui.ini.sample']),
    ],
    include_package_data=True,
    zip_safe=True,
    install_requires=get_requires(),
    tests_require=get_test_requires(),
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': ['iotgui = iotgui.cli:main'],
        'iot.cli': ['gui = iotgui.cli'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5']
)
