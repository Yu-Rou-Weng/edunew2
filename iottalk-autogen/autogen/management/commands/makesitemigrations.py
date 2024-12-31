from ._utlis import SubsysBaseCommand


class Command(SubsysBaseCommand):
    def handle(self, *args, **options):
        cmds = {
            site: ['python', 'manage.py', 'makemigrations', site, '--settings',
                   f'_.{site}_settings']
            for site in self.sites
        }
        self.batch_cmd(**cmds)
