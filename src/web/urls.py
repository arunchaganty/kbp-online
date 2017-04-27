from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^submit/$', views.submit, name='submit'),
    url(r'^explore/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.explore, name='explore'),
    url(r'^explore/$', views.explore, name='explore'),
    url(r'^$', views.home, name='home'),
]
