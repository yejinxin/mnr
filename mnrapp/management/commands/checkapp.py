from django.core.management.base import BaseCommand, CommandError
from mnrapp.models import Application 
from django.utils import timezone

from core.task import MnrTask

import logging
#logger = logging.getLogger('mnrapp')
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'check applications, remind users to recover them if necessary'

    def handle(self, *args, **options):
        apps = Application.objects.filter(status='DONE', recoverable=True)
        logger.info("start checking application")
        for app in apps:
            if app.expire_time < timezone.now():
                logger.info("Application %s should have been recovered!", app.pk)
                if app.mail_expire():
                    self.stdout.write(self.style.SUCCESS('Successfully mail related user for expired application "%s"' % app.pk))
                else:
                    self.stdout.write(self.style.ERROR('Failed to mail related user for expired application "%s"' % app.pk))
        logger.info("end checking application")
