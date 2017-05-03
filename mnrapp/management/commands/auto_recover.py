from django.core.management.base import BaseCommand, CommandError
from mnrapp.models import Application 
from django.utils import timezone

from core.task import MnrTask

import logging
#logger = logging.getLogger('mnrapp')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'start recovering an application'

    def handle(self, *args, **options):
        apps = Application.objects.filter(status='DONE', recoverable=True, autorecover=True)
        logger.info("start auto recover")
        task = MnrTask()
        for app in apps:
            if app.expire_time > timezone.now():
                logger.info("%s expire_time not come yet", app)
                continue
            task.recover(app)
            app.refresh_from_db()
            if app.status == 'FINISHED':
                self.stdout.write(self.style.SUCCESS('Successfully recovered application "%s"' % app.pk))
            else:
                self.stderr.write(self.style.ERROR('Recovering "%s" failed' % app.pk))
