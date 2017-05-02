from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^submit/$', views.submit, name='submit'),
    url(r'^explore/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.explore, name='explore'),
    url(r'^explore/$', views.explore, name='explore'),

    url(r'^interface/entity/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.interface, name='interface'),

    url(r'^api/document/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_document, name='api_document'),
    url(r'^api/suggested-mentions/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_suggested_mentions, name='api_suggested_mentions'),

    url(r'^$', views.home, name='home'),
]
