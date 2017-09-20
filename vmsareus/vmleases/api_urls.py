from django.conf.urls import url

from . import api_funcs

urlpatterns = [
    url(r'^list_branches$', api_funcs.list_branches),
]
