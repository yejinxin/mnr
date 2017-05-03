from django.core.management.base import BaseCommand, CommandError
from mnrapp.models import Application 

from core.task import MnrTask

import logging
#logger = logging.getLogger('mnrapp')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'start working for an application'

    def add_arguments(self, parser):
        parser.add_argument('apply_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for apply_id in options['apply_id']:
            try:
                app = Application.objects.get(pk=apply_id, status='PASSED')
            except Application.DoesNotExist:
                raise CommandError('Application "%s" does not exist or not PASSED' % apply_id)
            task = MnrTask()
            task.work(app)
            app.refresh_from_db()
            if app.status == 'DONE':
                self.stdout.write(self.style.SUCCESS('Successfully done application "%s"' % apply_id))
            else:
                self.stderr.write(self.style.ERROR('work for "%s" failed' % apply_id))
