from django import forms
from django.conf import settings
from .models import Application, Modification, RootModification, DiskModification, CpuMemModification, Review
from django.forms import BaseInlineFormSet, inlineformset_factory
from datetime import datetime, timedelta, tzinfo
#import pytz
from django.utils import timezone
from django.core.mail import mail_admins, BadHeaderError
from core.hostinfo import get_hostinfo
import re

class ContactForm(forms.Form):
    username = forms.CharField(max_length=32, widget=forms.HiddenInput)
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)

    def send_email(self):
        subject = 'FROM %s %s' % (self.cleaned_data['username'], self.cleaned_data['subject']) 
        message = self.cleaned_data['message']
        try:
            mail_admins(subject, message, fail_silently=True)
        except BadHeaderError:
            return False
        return True

class ApplicationFilterForm(forms.Form):
    APP_CHOICES = (
        ('', 'All application'),
        ('MY', 'My application'),
    )
    STATUS_CHOICES =(
        ('', 'ALL'),
        ('NEW', 'NEW'),
        ('DONE', 'DONE'),
        ('FINISHED', 'FINISHED'),
        ('ERROR', 'ERROR'),
    )
    category = forms.ChoiceField(required=False, choices=APP_CHOICES, initial='')
    status = forms.ChoiceField(required=False, choices=STATUS_CHOICES, initial='')


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ('apply_name', 'apply_desp', )
        widgets = {
            'apply_desp': forms.Textarea(attrs={'cols': 80, 'rows': 4}), 
        }

class DiskApplicationForm(ApplicationForm):
    def get_type(self):
        return 'DISK'

class RootApplicationForm(ApplicationForm):
    autorecover = forms.BooleanField(initial=True, required=False, help_text="Automatically recover all the modifications when expire time comes.")
    expire_time = forms.DateTimeField(initial=lambda : datetime.now() + timedelta(days=7), 
                       #input_formats=ApplicationForm.TIME_FORMAT,
                       widget=forms.DateTimeInput(attrs={'style': 'width: 160px', 'class': 'expire_time'}))
    #apply_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'style': 'width: 160px', 'class': 'apply_time'}))
    #apply_time = forms.DateTimeField(disabled=True)
    #readonly_fields = ('apply_time',)

    def get_type(self):
        return 'ROOT'

    def clean_expire_time(self):
        expire_time = self.cleaned_data.get('expire_time')
        now = timezone.now()
        #tomorrow = timezone.datetime.today() + timedelta(days=1)
        #expire_begin = timezone.datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day)
        #tz = timezone.get_current_timezone()
        #expire_begin = expire_begin.replace(tzinfo=tz)
        if expire_time < now: 
            raise forms.ValidationError("Expire time can not be past!")
        return expire_time

    class Meta(ApplicationForm.Meta):
        fields = ('apply_name', 'apply_desp', 'autorecover', 'expire_time')
    



class CpuMemApplicationForm(RootApplicationForm):
    autorecover = forms.BooleanField(initial=False, required=False, help_text="Automatically recover all the modifications when expire time comes.")
    def get_type(self):
        return 'CPUMEM'
    

class ModificationForm(forms.ModelForm):
#    def __init__(self, *args, **kwargs):
#        super(ModificationForm, self).__init__(*args, **kwargs)
#        ###self.fields['os_type'] = forms.CharField(max_length=10, initial='LINUX')


    def clean(self):
        cleaned_data = super(ModificationForm, self).clean()
        host = cleaned_data.get('host')
        prod_ip = cleaned_data.get('prod_ip')
        mng_ip = cleaned_data.get('mng_ip')
        if host and prod_ip and mng_ip:
            info = get_hostinfo(host, prod_ip, mng_ip, verbose='detail')
            if not info:
                raise forms.ValidationError("Host info not valid! Check host/prod_ip/mng_ip!")
            self.hostinfo = info
            os_type = info.get('os_type', None)
            if isinstance(self, RootModificationForm):
                if not os_type in ('LINUX', 'AIX', 'HPUX'):
                    raise forms.ValidationError("Only Linux/AIX/HPUX are supported!")
            elif isinstance(self, DiskModificationForm):
                if os_type != 'LINUX':
                    raise forms.ValidationError("Only Linux is supported!")
                if not info.get('vc', None):
                    raise forms.ValidationError("Sorry, this host lacks vCenter info!")
            elif isinstance(self, CpuMemModificationForm):
                if os_type != 'LINUX' and os_type != 'WINDOWS':
                    raise forms.ValidationError("Only x86 VM is supported!")
                if not info.get('vc', None):
                    raise forms.ValidationError("Sorry, this host lacks vCenter info!")
                

    def save(self, *args, **kwargs):
        self.instance.os_type = self.hostinfo.get('os_type', '')
        return super(ModificationForm, self).save(*args, **kwargs)

    class Meta:
        model = Modification
        fields = ('host', 'prod_ip', 'mng_ip', )
        widgets={
            'host': forms.TextInput(attrs={'class': 'acinput achost', 'size': '14'}),
            'prod_ip': forms.TextInput(attrs={'class': 'acinput acprod_ip', 'size': '14'}),
            'mng_ip': forms.TextInput(attrs={'class': 'acinput acmng_ip', 'size': '14'}),
        }

class RootModificationForm(ModificationForm):
    user = forms.CharField(max_length=16, initial='root', widget=forms.TextInput(attrs={'class': 'root_user', 'size': '6', 'onChange': 'root_user_change(this);'}))
    password = forms.CharField(max_length=32, initial='rootroot', widget=forms.TextInput(attrs={'class': 'new_pass', 'size': '6', 'readonly': 'readonly'}))
    def save(self, *args, **kwargs):
        self.instance.type = 'ROOT'
        return super(RootModificationForm, self).save(*args, **kwargs)

    class Meta:
        model = RootModification
        fields = ('host', 'prod_ip', 'mng_ip', 'user', 'password', )
        widgets={
            'host': forms.TextInput(attrs={'class': 'acinput achost', 'size': '14'}),
            'prod_ip': forms.TextInput(attrs={'class': 'acinput acprod_ip', 'size': '14'}),
            'mng_ip': forms.TextInput(attrs={'class': 'acinput acmng_ip', 'size': '14'}),
            #'user': forms.TextInput(attrs={'class': 'root_user', 'size': '6'}),
            #'password': forms.TextInput(attrs={'class': 'new_pass', 'size': '8', 'disabled': 'true'}),
        }

class DiskModificationForm(ModificationForm):
    FS_CHOICES=(
        ('/home/ap', '/home/ap'),
        ('/home/db', '/home/db'),
        ('/home/mw', '/home/mw'),
        ('/', '/'),
        ('/var', '/var'),
        ('/tmp', '/tmp'),
    )
    fs = forms.ChoiceField(choices=FS_CHOICES, initial='/home/ap')

    def save(self, *args, **kwargs):
        self.instance.type = 'DISK'
        return super(DiskModificationForm, self).save(*args, **kwargs)

    class Meta:
        model = DiskModification
        fields = ('host', 'prod_ip', 'mng_ip', 'fs', 'size',)
        widgets={
            'host': forms.TextInput(attrs={'class': 'acinput achost', 'size': '14'}),
            'prod_ip': forms.TextInput(attrs={'class': 'acinput acprod_ip', 'size': '14'}),
            'mng_ip': forms.TextInput(attrs={'class': 'acinput acmng_ip', 'size': '14'}),
            'fs': forms.TextInput(attrs={'size': '12'}),
            'size': forms.NumberInput(attrs={'min': '1', 'max': '500'}),
        }

    
class CpuMemModificationForm(ModificationForm):
    def save(self, *args, **kwargs):
        self.instance.type = 'CPUMEM'
        return super(CpuMemModificationForm, self).save(*args, **kwargs)

    class Meta:
        model = CpuMemModification
        fields = ('host', 'prod_ip', 'mng_ip', 'cpu_ori', 'cpu_new', 'mem_ori', 'mem_new' )
        widgets={
            'host': forms.TextInput(attrs={'class': 'acinput achost', 'size': '14'}),
            'prod_ip': forms.TextInput(attrs={'class': 'acinput acprod_ip', 'size': '14'}),
            'mng_ip': forms.TextInput(attrs={'class': 'acinput acmng_ip', 'size': '14'}),
            'cpu_ori': forms.NumberInput(attrs={'placeholder': 'CPU_O', 'min': '1', 'max': '100'}),
            'cpu_new': forms.NumberInput(attrs={'placeholder': 'CPU_N', 'min': '1', 'max': '100'}),
            'mem_ori': forms.NumberInput(attrs={'placeholder': 'MEM_O', 'min': '1', 'max': '1024'}),
            'mem_new': forms.NumberInput(attrs={'placeholder': 'MEM_N', 'min': '1', 'max': '1024'}),
        }



RootModsInlineFormSet = inlineformset_factory(Application, RootModification, form=RootModificationForm, min_num=1, validate_min=True, extra=0, )
DiskModsInlineFormSet = inlineformset_factory(Application, DiskModification, form=DiskModificationForm, min_num=1, validate_min=True, extra=0, )
CpuMemModsInlineFormSet = inlineformset_factory(Application, CpuMemModification, form=CpuMemModificationForm, min_num=1, validate_min=True, extra=0, )

ReviewsInlineFormSet = inlineformset_factory(Application, Review, can_delete=False, extra=0, fields=('comment',))





