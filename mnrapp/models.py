# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings

# Create your models here.

@python_2_unicode_compatible
class Application(models.Model):
    TYPE_CHOICES = (
        ('ROOT', 'ROOT'),
        ('DISK', 'DISK'),
        ('CPUMEM', 'CPU/MEMORY'),
        ('MIXED', 'MIXED'),
    )
    STATUS_CHOICES = (
        ('NEW', 'NEW'),
        ('PASSED', 'PASSED'),
        ('REJECTED', 'REJECTED'),
        ('DOING', 'DOING'),
        ('DONE', 'DONE'),
        ('RECOVERING', 'RECOVERING'),
        ('FINISHED', 'FINISHED'),
        ('ERROR', 'ERROR'),
        ('ABANDONED', 'ABANDONED'),
    )
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    apply_time = models.DateTimeField(auto_now_add=True)
    apply_name = models.CharField("Application name", max_length=100)
    apply_desp = models.TextField("Application description")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='NEW')
    recoverable = models.BooleanField(default=False)
    autorecover = models.BooleanField(default=False, help_text="Automatically recover modification when expire time comes.")
    expire_time = models.DateTimeField(null=True, blank=True)

    @property
    def modifications(self):
        if self.type == 'ROOT':
            return self.rootmodifications
        elif self.type == 'DISK':
            return self.diskmodifications
        elif self.type == 'CPUMEM':
            return self.cpumemmodifications

    def mods_num(self):
        return len(self.modifications.all())
    
    def get_recipients(self):
        recipients = {self.applicant.email}
        for review in self.reviews.all():
            recipients.add(review.reviewer.email)
        return list(recipients)

    def mail_new(self):
        if not self.status == 'NEW':
            return False
        recipient_list = [username + '@ccb.com' for username in settings.STAFF ]   
        subject = 'New MNR %s application %s to be reviewed' % (self.type, self.pk)
        message = self.apply_name
        from_email = 'MNR@ccb.com'
        return send_mail(subject, message, from_email, recipient_list)

    def mail_done(self):
        if not self.status == 'DONE':
            return False
        recipient_list = self.get_recipients()
        subject = 'Application done'
        message = u'All modification done in %s application %s %s. ' % (self.type, self.pk, self.apply_name)
        if self.recoverable:
            if self.autorecover and self.expire_time:
                message += u' They will be automatically recovered at %s.' % (timezone.localtime(self.expire_time).strftime("%Y-%m-%d %H:%M"),)
            elif self.expire_time:
                message += u' Please recover these modification on detail page before %s.' % (timezone.localtime(self.expire_time).strftime("%Y-%m-%d %H:%M"),)
        from_email = 'MNR@ccb.com'
        return send_mail(subject, message, from_email, recipient_list)

    def mail_expire(self):
        if not self.status == 'DONE':
            return False
        recipient_list = self.get_recipients()
        subject = 'Application has expired'
        message = u'%s application %s %s has expired! Please recover it.' % (self.type, self.pk, self.apply_name)
        from_email = 'MNR@ccb.com'
        return send_mail(subject, message, from_email, recipient_list)

    def mail_finished(self):
        if not self.status == 'FINISHED':
            return False
        recipient_list = self.get_recipients()
        subject = 'Application recovered'
        message = u'All modification recovered in %s application %s \n %s' % (self.type, self.pk, self.apply_name)
        from_email = 'MNR@ccb.com'
        return send_mail(subject, message, from_email, recipient_list)



    def update_status(self, status=None, user=None):
        if status == 'TESTING':
            pass
        elif status == 'PASSED' or status == 'REJECTED':
            self.status = status
            self.save()
            review = Review(action=status, application=self)
            if user:
                review.reviewer = user
            review.save()
        elif status == 'DOING':
            for mod in self.modifications.all():
                if mod.status == 'NEW':
                    mod.status = 'DOING'
                    mod.save()
            self.status = 'DOING'
            self.save()
        elif status == 'DONE':
            done_flag = True
            error_flag = False
            for mod in self.modifications.all():
                if mod.status != 'DONE':
                    done_flag = False
                if mod.status == 'ERROR':
                    error_flag = True
            if done_flag:
                self.status = 'DONE'
                self.save()
                self.mail_done()
            if error_flag:
                self.status = 'ERROR'
                self.save()
        elif status == 'RECOVERING':
            for mod in self.modifications.all():
                if mod.status == 'DONE':
                    mod.status = 'RECOVERING'
                    mod.save()
            self.status = 'RECOVERING'
            self.save()
        elif status == 'FINISHED':
            done_flag = True
            error_flag = False
            for mod in self.modifications.all():
                if mod.status != 'FINISHED':
                    done_flag = False
                if mod.status == 'ERROR':
                    error_flag = True
            if done_flag:
                self.status = 'FINISHED'
            if error_flag:
                self.status = 'ERROR'
            self.save()
        elif status is None:
            raise Exception("Not implemented")

    def __str__(self):
        return '%s %s - %d mods' % (self.pk, self.apply_name, self.mods_num())



@python_2_unicode_compatible
class Review(models.Model):
    ACTION_CHOICES = (
        ('PASSED', 'APPROVE'),
        ('REJECTED', 'REJECT'),
        ('RECOVERED', 'RECOVER'),
        ('OTHER', 'OTHER'),
    )
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='reviews', verbose_name="Application ID")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    comment = models.CharField(max_length=100)
    review_time = models.DateTimeField(auto_now_add=True)
    reviewer = models.ForeignKey(User)

    def get_description(self):
        return u'%s %s this application at %s.' % (self.reviewer.username, self.action, timezone.localtime(self.review_time).strftime("%Y-%m-%d %H:%M"), )
    
    def __str__(self):
        return self.comment


class Modification(models.Model):
    TYPE_CHOICES = (
        ('ROOT', 'ROOT'),
        ('DISK', 'DISK'),
        ('CPUMEM', 'CPU/MEMORY'),
    )
    STATUS_CHOICES = (
        ('NEW', 'NEW'),
        ('DOING', 'DOING'),
        ('DONE', 'DONE'),
        ('RECOVERING', 'RECOVERING'),
        ('FINISHED', 'FINISHED'),
        ('ERROR', 'ERROR'),
    )
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='%(class)ss', verbose_name="Application ID")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='ROOT')
    host = models.CharField(max_length=16, )
    prod_ip = models.GenericIPAddressField("Production IP", protocol='IPv4')
    mng_ip = models.GenericIPAddressField("Management IP", protocol='IPv4')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='NEW')
    message = models.CharField(max_length=255, editable=False)

    class Meta:
        abstract = True
    
#    def __str__(self):
#        return '%s %s'%(self.type, self.host)


@python_2_unicode_compatible
class RootModification(Modification):
    OS_TYPE_CHOICES = (
        ('LINUX', 'LINUX'),
        ('AIX', 'AIX'),
        ('HPUX', 'HPUX'),
    )
    os_type = models.CharField(max_length=6, choices=OS_TYPE_CHOICES, default='LINUX')
    user = models.CharField(max_length=16, default='root')
    password = models.CharField(max_length=32, default='rootroot')
    ori_password = models.CharField("original password hash", max_length=512, editable=False, default='')

    def __str__(self):
        return '%s %s'%(self.host, self.user)
    

@python_2_unicode_compatible
class DiskModification(Modification):
    OS_TYPE_CHOICES = (
        ('LINUX', 'LINUX'),
    )
    os_type = models.CharField(max_length=6, choices=OS_TYPE_CHOICES, default='LINUX')
    fs = models.CharField("filesystem", max_length=50, validators=[RegexValidator(r'/[^\0]*', message="Enter a valid filesystem path."), ])
    size = models.PositiveSmallIntegerField("Fs Size", validators=[MinValueValidator(1), MaxValueValidator(1024),])

    def __str__(self):
        return '%s %s'%(self.host, self.fs)

@python_2_unicode_compatible
class CpuMemModification(Modification):
    OS_TYPE_CHOICES = (
        ('LINUX', 'LINUX'),
        ('WIN', 'WINDOWS'),
    )
    os_type = models.CharField(max_length=6, choices=OS_TYPE_CHOICES, default='LINUX')
    cpu_ori = models.PositiveSmallIntegerField("Original Cpu Num", validators=[MinValueValidator(1), MaxValueValidator(256),])
    cpu_new = models.PositiveSmallIntegerField("New Cpu Num", validators=[MinValueValidator(1), MaxValueValidator(256),])
    mem_ori = models.PositiveSmallIntegerField("Original Mem Num", validators=[MinValueValidator(1), MaxValueValidator(1024),])
    mem_new = models.PositiveSmallIntegerField("New Mem Num", validators=[MinValueValidator(1), MaxValueValidator(1024),])

    def __str__(self):
        return '%s %sC%sG'%(self.host, self.cpu_new, self.mem_new)

