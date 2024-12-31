import os
import pty
import re
import subprocess

from contextlib import suppress
from queue import Queue, Empty
from random import randint
from signal import SIGTERM
from threading import Thread

from django.conf import settings
from django.core.management.base import CommandError

from ._utlis import SubsysBaseCommand, first


class Command(SubsysBaseCommand):
    '''
    Run XTalk subsystem development server.
    '''

    def add_arguments(self, parser):
        # e.g. --site aitalk:12345 --site datatalk:12346
        parser.add_argument(
            '-s', '--site', action='append', type=str, dest='sites',
            help='<site name>[:<port>]')

    def parse_site(self, s):
        name, _, port = s.partition(':')
        port = int(port) if port else None
        return name, port

    def interactive_session(self, site: str, cmd: list, pidq: Queue, io: Queue):
        # capture all output
        # see: https://stackoverflow.com/a/41593121
        master, slave = pty.openpty()  # master fd and slave fd

        p = subprocess.Popen(
            cmd,
            cwd=settings.BASE_DIR,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            encoding='utf-8',
            universal_newlines=True,
            start_new_session=True,
        )
        pidq.put(p.pid)
        os.close(slave)

        delm = b'\r\n'
        buf = b''

        try:
            while True:
                x = os.read(master, 10240)
                buf += x

                lines = buf.split(delm)
                if len(lines) == 1:  # no newline char in buffer
                    continue

                buf = lines[-1]
                for i in lines[:-1]:
                    io.put((site, i + delm))
        except OSError as e:
            p.terminate()
            p.kill()
            raise e

    def handle(self, *args, **kwargs):
        self.pids = []
        try:
            self._handle(self, *args, **kwargs)
        except KeyboardInterrupt:
            pass
        finally:
            for pid in self.pids:
                with suppress(OSError):
                    os.kill(pid, SIGTERM)

    def _handle(self, *args, **options):
        site_candidate = self.sites
        default_port = 8000  # for port allocation, default starts from 8000
        sites = map(self.parse_site, options['sites'])
        ts = []  # [(site, thread obj)], do not use `dict`, since I want to keep the order
        pidq = Queue()
        ioq = Queue()

        for name, port in sites:
            if name not in site_candidate:
                raise CommandError(
                    f"Unknown site: '{name}'. "
                    f"Please put the site settings file in '{self.settings_dir}'.")

            if port is None:
                port = default_port
                default_port += 1

            cmd = ['./manage.py', 'runserver', '--settings', f'_.{name}_settings',
                   f'0.0.0.0:{port}']
            t = Thread(target=self.interactive_session, args=(name, cmd, pidq, ioq))
            t.daemon = True
            t.start()
            ts.append((name, t))

            self.stdout.write(f'=> start site {name} on port {port}\n')

        self.pids = [pidq.get() for _ in ts]

        # for repeat the last shown color
        color_pat = re.compile(r'\x1b\[[0-9;]*m')
        color_state = {site: '\033[m' for site in map(first, ts)}
        prefixes = {
            site: f'{site} ({pid})'
            for site, pid in zip(map(first, ts), self.pids)
        }
        width = max(map(len, prefixes.values()))
        prefixes = {
            site: f'\033[3{randint(2, 6)}m{p.ljust(width)} |\033[m '
            for site, p in prefixes.items()
        }

        while True:
            with suppress(Empty):
                site, line = ioq.get()
                line = line.decode()
                self.stdout.write(f'{prefixes[site]}'
                                  f'{color_state[site]}{line}')

                color_codes = color_pat.findall(line)
                if color_codes:
                    color_state[site] = color_codes[-1]

                self.stdout.flush()
