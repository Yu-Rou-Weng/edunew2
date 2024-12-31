import os

from django.conf import settings

from ._utlis import SubsysBaseCommand


class Command(SubsysBaseCommand):
    def handle(self, *args, **options):
        cmds = {
            site: ['pytest', '-c', os.path.join(settings.BASE_DIR, site, 'pytest.ini')]
            for site in self.sites
        }
        self.batch_cmd(**cmds)
