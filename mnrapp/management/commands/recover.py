from django.core.management.base import BaseCommand, CommandError
from mnrapp.models import Application 

from core.task import MnrTask

import logging
#logger = logging.getLogger('mnrapp')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'start recovering an application'

    def add_arguments(self, parser):
        parser.add_argument('apply_id', nargs='+', type=int)
#        parser.add_argument(
#            '--force',
#            action='store_true',
#            dest='force',
#            default=False,
#            help='Force to recover application, ignoring expire_time',
#        )

    def handle(self, *args, **options):
#        force = options['force']
        for apply_id in options['apply_id']:
            try:
                app = Application.objects.get(pk=apply_id, status='DONE', recoverable=True)
            except Application.DoesNotExist:
                raise CommandError('Application "%s" does not exist or not recoverable' % apply_id)
            #if not force and app.expire_time > timezone.now():
            #if app.expire_time > timezone.now():
            #    raise CommandError('Application "%s" expire_time not come yet' % app)
            task = MnrTask()
            task.recover(app)
            app.refresh_from_db()
            if app.status == 'FINISHED':
                self.stdout.write(self.style.SUCCESS('Successfully recovered application "%s"' % apply_id))
            else:
                self.stderr.write(self.style.ERROR('Recovering "%s" failed' % apply_id))
