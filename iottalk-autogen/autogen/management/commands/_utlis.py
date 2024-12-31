import os

from collections import OrderedDict
from pathlib import Path
from subprocess import call

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def first(ls):
    return ls[0]


class SubsysBaseCommand(BaseCommand):
    '''
    The base command class for IoTtalk Xtalk subsystem.
    '''

    @property
    def settings_dir(self):
        return Path(settings.BASE_DIR) / '_'

    @property
    def sites(self):
        p = Path(settings.BASE_DIR) / '_'
        suffix = '_settings.py'
        return [i.split(suffix)[0] for i in os.listdir(p) if i.endswith(suffix)]

    def batch_cmd(self, **cmds):
        '''
        Run multiple cmds without interrupted.

        Raise ``CommandError`` if any one of the cmd return non-zero value.

        :param cmds: where the key is the site name and
            the value is the corresponding command.
            A command should be a list of ``str``.
        '''
        rets = OrderedDict()
        for site, cmd in cmds.items():
            self.stdout.write(f'==> Execute command: {self.cmd_str(cmd)}')

            env = os.environ.copy()  # cleanup current env
            del env['DJANGO_SETTINGS_MODULE']
            del env['TZ']

            rets[site] = call(cmd, cwd=settings.BASE_DIR, env=env)

        errs = []
        for site, ret in rets.items():
            if ret == 0:
                continue

            errs.append(f'site {site} exited with {ret} on {self.cmd_str(cmds[site])}')

        if errs:
            raise CommandError('\n\t' + '\n\t'.join(errs))

    @staticmethod
    def cmd_str(cmd):
        return ' '.join(cmd)
