from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, render_to_response
from django.shortcuts import get_object_or_404

# Create your views here.
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, FormMixin
from django.views.generic import View, CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
#from django.contrib.auth.forms import AuthenticationForm
#from django.contrib.auth.decorators import login_required
#from django.forms import inlineformset_factory
from .forms import ( ContactForm, ApplicationFilterForm, RootApplicationForm, DiskApplicationForm, CpuMemApplicationForm, 
                   RootModsInlineFormSet, DiskModsInlineFormSet, CpuMemModsInlineFormSet, ReviewsInlineFormSet )
from .models import Application, Modification
from core.util import call_mc

class HomePageView(TemplateView):
    template_name = "mnrapp/home.html"

class AboutView(TemplateView):
    template_name = "mnrapp/about.html"

class ThanksView(TemplateView):
    template_name = "mnrapp/thanks.html"

class ContactView(LoginRequiredMixin, FormView):
    form_class = ContactForm
    template_name = "mnrapp/contact.html"
    success_url = reverse_lazy('thanks')

    def get_initial(self):
        initial = super(ContactView, self).get_initial()
        initial.update({"username": self.request.user.username})
        return initial
    
    def form_valid(self, form):
        if not form.send_email():
            return render_to_response('mnrapp/error.html', {'message': 'Bad message!'})
        return super(ContactView, self).form_valid(form)
            
class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "mnrapp/user_profile.html"

    def get_context_data(self, **kwargs):
        context = super(UserProfileView, self).get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs.get('pk'))
        if user == self.request.user:
            prefix = 'You have '
        else:
            prefix = '%s has ' % user.get_short_name()
        context['prefix'] = prefix
        context['user'] = user
        return context


class BaseApplyCreateView(LoginRequiredMixin, CreateView):
    model = Application
    template_name = "mnrapp/apply_for.html"
    success_url = reverse_lazy('application')

    def get_mod_formset_class(self):
        return ModsInlineFormSet

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ModInlineFormSetClass = self.get_mod_formset_class()
        mods_formset = ModInlineFormSetClass()
        return self.render_to_response(self.get_context_data(form=form, mods_formset=mods_formset))

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ModInlineFormSetClass = self.get_mod_formset_class()
        mods_formset = ModInlineFormSetClass(self.request.POST, instance=self.object)
        if form.is_valid() and mods_formset.is_valid():
            return self.form_valid(form, mods_formset)
        else:
            return self.form_invalid(form, mods_formset)

    def form_valid(self, form, mods_formset):
        return super(BaseApplyCreateView, self).form_valid(form)

    def form_invalid(self, form, mods_formset):
        return self.render_to_response(self.get_context_data(form=form, mods_formset=mods_formset))


class ApplyRootCreateView(BaseApplyCreateView):
    form_class = RootApplicationForm

    def get_mod_formset_class(self):
        return RootModsInlineFormSet

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Apply for root privelege'
        return super(ApplyRootCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form, mods_formset):
        self.object = form.save(commit=False)
        self.object.applicant = self.request.user
        self.object.recoverable = True
        self.object.type = 'ROOT'
        self.object.save()
        mods_formset.instance = self.object
        mods_formset.save()
        self.object.mail_new()
        return HttpResponseRedirect(self.get_success_url())
    
  

class ApplyDiskCreateView(BaseApplyCreateView):
    form_class = DiskApplicationForm 

    def get_mod_formset_class(self):
        return DiskModsInlineFormSet

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Apply for disk space'
        return super(ApplyDiskCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form, mods_formset):
        self.object = form.save(commit=False)
        self.object.applicant = self.request.user
        self.object.recoverable = False
        self.object.type = 'DISK'
        self.object.save()
        mods_formset.instance = self.object
        mods_formset.save()
        self.object.mail_new()
        return HttpResponseRedirect(self.get_success_url())


class ApplyCpuMemCreateView(BaseApplyCreateView):
    form_class = CpuMemApplicationForm 

    def get_mod_formset_class(self):
        return CpuMemModsInlineFormSet

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Apply for VM CPU/MEM'
        return super(ApplyCpuMemCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form, mods_formset):
        self.object = form.save(commit=False)
        self.object.applicant = self.request.user
        self.object.recoverable = True
        self.object.type = 'CPUMEM'
        self.object.save()
        mods_formset.instance = self.object
        mods_formset.save()
        self.object.mail_new()
        return HttpResponseRedirect(self.get_success_url())

class BaseApplicationUpdateView(UserPassesTestMixin, UpdateView):
    model = Application
    success_url = reverse_lazy('application')
    template_name = 'mnrapp/apply_for.html'
    #context_object_name = 'application'
    raise_exception = True
    
    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        if 'action' not in kwargs:
            kwargs['action'] = 'REVIEW'
        return super(BaseApplicationUpdateView, self).get_context_data(**kwargs)

    def get(self, request, pk, *args, **kwargs):
        self.object = kwargs.get('object', None)
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ModInlineFormSetClass = self.get_mod_formset_class()
        mods_formset = ModInlineFormSetClass(instance=self.object)
        return self.render_to_response(self.get_context_data(form=form, mods_formset=mods_formset))

    def post(self, request, pk, *args, **kwargs):
        self.object = kwargs.get('object', None)
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ModInlineFormSetClass = self.get_mod_formset_class()
        mods_formset = ModInlineFormSetClass(self.request.POST, instance=self.object)
        if form.is_valid() and mods_formset.is_valid():
            return self.form_valid(form, mods_formset)
        else:
            return self.form_invalid(form, mods_formset)

    def form_invalid(self, form, mods_formset):
        return self.render_to_response(self.get_context_data(form=form, mods_formset=mods_formset))

    def form_valid(self, form, mods_formset):
        review = self.request.POST.get('review', False)
        if review == 'PASSED' or review == 'REJECTED':
            self.object.status = review
        else:
            return render_to_response('mnrapp/error.html', {'message': 'Review operation error!'})
        self.object.update_status(review, self.request.user)
        mods_formset.save()
        call_mc('work %s' % self.object.pk)
        return render_to_response('mnrapp/success.html', {'message': 'Review operation done!'})

class RootApplicationUpdateView(BaseApplicationUpdateView):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.username in settings.TRUSTEE

    def get(self, request, pk, *args, **kwargs):
        self.object = kwargs.get('object', None)
        #disallow TRUSTEE to review other TRUSTEE's application
        if not self.request.user.is_staff and self.request.user != self.object.applicant:
            return HttpResponseForbidden('403 FORBIDDEN')
        return super(RootApplicationUpdateView, self).get(request, pk, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        self.object = kwargs.get('object', None)
        #disallow TRUSTEE to review other TRUSTEE's application
        if not self.request.user.is_staff and self.request.user != self.object.applicant:
            return HttpResponseForbidden('403 FORBIDDEN')
        return super(RootApplicationUpdateView, self).post(request, pk, *args, **kwargs)
        
    def get_form_class(self):
        return RootApplicationForm

    def get_mod_formset_class(self):
        return RootModsInlineFormSet

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Apply for root privelete'
        return super(RootApplicationUpdateView, self).get_context_data(**kwargs)

class DiskApplicationUpdateView(BaseApplicationUpdateView):
    def get_form_class(self):
        return DiskApplicationForm

    def get_mod_formset_class(self):
        return DiskModsInlineFormSet

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Apply for disk space'
        return super(DiskApplicationUpdateView, self).get_context_data(**kwargs)

class CpuMemApplicationUpdateView(BaseApplicationUpdateView):
    def get_form_class(self):
        return CpuMemApplicationForm

    def get_mod_formset_class(self):
        return CpuMemModsInlineFormSet

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = 'Apply for VM CPU/MEM'
        return super(CpuMemApplicationUpdateView, self).get_context_data(**kwargs)

class ApplicationUpdateView(View):
    def configure(self, pk):
        self.object = get_object_or_404(Application, pk=pk, status='NEW') 
        if self.object.type == 'ROOT':
            self.view = RootApplicationUpdateView.as_view()
        elif self.object.type == 'DISK':
            self.view = DiskApplicationUpdateView.as_view()
        elif self.object.type == 'CPUMEM':
            self.view = CpuMemApplicationUpdateView.as_view()
        else:
            return HttpResponseForbidden("403 FORBIDDEN")

    def get(self, request, pk, *args, **kwargs):
        ret = self.configure(pk)
        if isinstance(ret, HttpResponse):
            return ret
        return self.view(request, pk, object=self.object, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        ret = self.configure(pk)
        if isinstance(ret, HttpResponse):
            return ret
        return self.view(request, pk, object=self.object, *args, **kwargs)

#class ApplicationUpdateViewBak(UserPassesTestMixin, UpdateView):
#    model = Application
#    success_url = reverse_lazy('application')
#    #template_name = 'mnrapp/apply_root.html'
#    #form_class = ApplicationForm
#    raise_exception = True
#    
#    def test_func(self):
#        return self.request.user.is_staff
#    
#    def configure(self, apply_id):
#        self.object = get_object_or_404(Application, pk=apply_id) 
#        if self.object.status != 'NEW':
#            return render_to_response('mnrapp/error.html', {'message': 'Application status error!'})        
#        self.lookup = {
#            'ROOT': {
#                'title': 'Apply for root privelete',
#                'form_class': RootApplicationForm,
#                'formset_class': RootModsInlineFormSet,
#                'template_name': 'mnrapp/apply_for.html',
#                'form_valid': self.root_form_valid,
#            },
#            'DISK': {
#                'title': 'Apply for disk space',
#                'form_class': DiskApplicationForm,
#                'formset_class': DiskModsInlineFormSet,
#                'template_name': 'mnrapp/apply_for.html',
#                'form_valid': self.root_form_valid,
#            },
#            'CPUMEM': {
#                'title': 'Apply for VM CPU/MEM',
#                'form_class': CpuMemApplicationForm,
#                'formset_class': CpuMemModsInlineFormSet,
#                'template_name': 'mnrapp/apply_for.html',
#                'form_valid': self.root_form_valid,
#            },
#        }
#        self.type = self.object.type
#        self.template_name = self.lookup[self.type].get('template_name')
#
#    def get_form_class(self):
#        return self.lookup[self.type].get('form_class')
#
#    def get_mod_formset_class(self):
#        return self.lookup[self.type].get('formset_class')
#
#    def get_context_data(self, **kwargs):
#        if 'title' not in kwargs:
#            kwargs['title'] = self.lookup[self.type].get('title')
#        if 'app_type' not in kwargs:
#            kwargs['app_type'] = self.type
#        if 'action' not in kwargs:
#            kwargs['action'] = 'REVIEW'
#        return super(ApplicationUpdateView, self).get_context_data(**kwargs)
#
#    def get(self, request, pk, *args, **kwargs):
#        ret = self.configure(pk)
#        if isinstance(ret, HttpResponse):
#            return ret
#        form_class = self.get_form_class()
#        form = self.get_form(form_class)
#        ModInlineFormSetClass = self.get_mod_formset_class()
#        mods_formset = ModInlineFormSetClass(instance=self.object)
#        return self.render_to_response(
#            self.get_context_data(form=form,
#                                  mods_formset=mods_formset))
#
#    def post(self, request, pk, *args, **kwargs):
#        ret = self.configure(pk)
#        if isinstance(ret, HttpResponse):
#            return ret
#        form_class = self.get_form_class()
#        form = self.get_form(form_class)
#        ModInlineFormSetClass = self.get_mod_formset_class()
#        mods_formset = ModInlineFormSetClass(self.request.POST, instance=self.object)
#        if form.is_valid() and mods_formset.is_valid():
#            return self.form_valid(form, mods_formset)
#        else:
#            return self.form_invalid(form, mods_formset)
#
#    def form_valid(self, form, mods_formset):
#        return self.lookup[self.type].get('form_valid')(form, mods_formset)
#
#    def form_invalid(self, form, mods_formset):
#        return self.render_to_response(
#            self.get_context_data(form=form,
#                                  mods_formset=mods_formset))
#
#    def root_form_valid(self, form, mods_formset):
#        review = self.request.POST.get('review', False)
#        if review == 'PASSED' or review == 'REJECTED':
#            self.object.status = review
#        else:
#            return render_to_response('mnrapp/error.html', {'message': 'Review operation error!'})
#        self.object.update_status(review, self.request.user)
#        mods_formset.save()
#        call_mc('work %s' % self.object.pk)
#        return render_to_response('mnrapp/success.html', {'message': 'Review operation done!'})
#

class ApplicationListView(LoginRequiredMixin,  ListView):
    model = Application
    template_name = 'mnrapp/application.html'
    context_object_name = "application_list"
    paginate_by = 20

    def get_queryset(self):
        form = ApplicationFilterForm(self.request.GET)
        form.is_valid()
        category = form.cleaned_data.get('category', '')
        status = form.cleaned_data.get('status', '')
        self.initial = {'category': category, 'status': status}
        if category == 'MY':
            qs = Application.objects.filter(applicant=self.request.user).order_by('-id')
        else:
            qs = Application.objects.all().order_by('-id')
        if status:
            qs = qs.filter(status=status) 
        return qs

    def get_context_data(self, **kwargs):
        context = super(ApplicationListView, self).get_context_data(**kwargs)
        context['form'] = ApplicationFilterForm(self.initial)
        context['TRUSTEE'] = settings.TRUSTEE
        return context


class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = 'mnrapp/application_detail.html'
    context_object_name = "application"
    #pk_url_kwarg = "id"

class RecoverNowView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        app = get_object_or_404(Application, pk=pk, recoverable=True)
        if app.status != 'DONE':
            return render_to_response('mnrapp/error.html', {'message': 'Application status error!'}) 
        if not request.user.is_staff and request.user != app.applicant:
            return HttpResponseForbidden('403 FORBIDDEN')
        call_mc('recover %s' % app.pk)
        return HttpResponseRedirect(reverse_lazy('application_detail', args=(app.pk,)))


