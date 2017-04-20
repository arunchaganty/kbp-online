from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^submit/$', views.submit, name='submit'),
    url(r'^explore/$', views.explore, name='explore'), # TODO: expand to include different documents, etc.
    url(r'^$', views.home, name='home'),
]
