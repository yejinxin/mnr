from django.conf.urls import url
from django.views.decorators.cache import cache_page

from . import views
from . import api
#from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r'^$', views.HomePageView.as_view(), name='home'),
    url(r'^contact/$', views.ContactView.as_view(), name='contact'),
    url(r'^thanks/$', views.ThanksView.as_view(), name='thanks'),
    url(r'^about/$', views.AboutView.as_view(), name='about'),
    url(r'^profile/(?P<pk>[\d]+)/$', cache_page(60*15)(views.UserProfileView.as_view()), name='profile'),
    url(r'^application/$', views.ApplicationListView.as_view(), name='application'),
    url(r'^application/review/(?P<pk>[\d]+)/$', views.ApplicationUpdateView.as_view(), name='application_review'),
    url(r'^application/recover/(?P<pk>[\d]+)/$', views.RecoverNowView.as_view(), name='application_recover'),
    url(r'^application/detail/(?P<pk>[\d]+)/$', views.ApplicationDetailView.as_view(), name='application_detail'),
    #url(r'^application/(?P<pk>[\d]+)/$', views.ApplicationDetailView.as_view(), name='application_detail'),
    url(r'^apply/root/$', views.ApplyRootCreateView.as_view(), name='apply_root'),
    url(r'^apply/disk/$', views.ApplyDiskCreateView.as_view(), name='apply_disk'),
    url(r'^apply/cpumem/$', views.ApplyCpuMemCreateView.as_view(), name='apply_cpumem'),
    url(r'api/host.json/$', api.HostInfoView.as_view(), name='api_hostinfo'),
]
