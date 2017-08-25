from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.vm_list, name='vm_list'),
    url(r'^vm/(?P<pk>\d+)/$', views.vm_detail, name='vm_detail'),
    url(r'^vm/new/$', views.vm_new, name='vm_new'),
    url(r'^vm/(?P<pk>\d+)/edit/$', views.vm_edit, name='vm_edit'),
    url(r'^vm/(?P<pk>\d+)/remove/$', views.vm_remove, name='vm_remove'),
    url(r'^vm/(?P<pk>\d+)/extend/$', views.vm_extend, name='vm_extend'),
]
