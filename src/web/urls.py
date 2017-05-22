from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^submit/$', views.submit, name='submit'),

    url(r'^explore/corpus/(?P<corpus_tag>[a-zA-Z_0-9.-]+)/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.explore_corpus, name='explore_corpus'),
    url(r'^explore/corpus/(?P<corpus_tag>[a-zA-Z_0-9.-]+)/$', views.explore_corpus, name='explore_corpus'),

    url(r'^explore/submission/(?P<submission_id>[a-zA-Z_0-9.]+)/$', views.explore_submission, name='explore_submission'),

    url(r'tasks/do/$', views.do_task, name="do_task"),

    url(r'^api/document/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_document, name='api_document'),
    url(r'^api/suggested-mentions/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_suggested_mentions, name='api_suggested_mentions'),
    url(r'^api/suggested-mention-pairs/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_suggested_mention_pairs, name='api_suggested_mention_pairs'),
    url(r'^api/suggested-mention-pairs/(?P<doc_id>[a-zA-Z_0-9.]+)/(?P<subject_id>[0-9]+-[0-9]+):(?P<object_id>[0-9]+-[0-9]+)/$', views.api_suggested_mention_pairs, name='api_suggested_mention_pairs'),

    url(r'^api/evaluation-mentions/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_evaluation_mentions, name='api_evaluation_mentions'),
    url(r'^api/evaluation-mention-pairs/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_evaluation_mention_pairs, name='api_evaluation_mention_pairs'),
    url(r'^api/evaluation-mention-pairs/(?P<doc_id>[a-zA-Z_0-9.]+)/(?P<subject_id>[0-9]+-[0-9]+):(?P<object_id>[0-9]+-[0-9]+)/$', views.api_evaluation_mention_pairs, name='api_evaluation_mention_pairs'),

    url(r'^api/submission/(?P<submission_id>[0-9]+)/$', views.api_submission_entries, name='api_submission_entries'),
    url(r'^api/corpus/(?P<corpus_tag>[0-9a-zA-Z._]+)/$', views.api_corpus_listing, name='api_corpus_listing'),

    # These are all test interfaces.
    url(r'^interface/(?P<task>entity)/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.interface, name='interface'),
    url(r'^interface/(?P<task>relation)/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.interface, name='interface'),
    url(r'^interface/(?P<task>relation)/(?P<doc_id>[a-zA-Z_0-9.]+)/(?P<subject_id>[0-9]+-[0-9]+):(?P<object_id>[0-9]+-[0-9]+)/$', views.interface, name='interface'),

    url(r'^$', views.home, name='home'),
]
