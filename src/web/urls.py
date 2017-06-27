from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^submissions/$', views.submissions, name='submissions'),
    url(r'^submissions/(?P<submission_id>[0-9]+)/delete/$', views.submissions_delete, name='submissions_delete'),
    url(r'^submissions/(?P<submission_id>[0-9]+)/download/(?P<resource>log)/$', views.submissions_download, name='submissions_delete'),
    url(r'^submissions/(?P<submission_id>[0-9]+)/download/(?P<resource>kb)/$', views.submissions_download, name='submissions_delete'),

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
    url(r'^api/evaluation-relations/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.api_evaluation_relations, name='api_evaluation_relations'),

    url(r'^api/submission/(?P<submission_id>[0-9]+)/$', views.api_submission_entries, name='api_submission_entries'),
    url(r'^api/corpus/(?P<corpus_tag>[0-9a-zA-Z._]+)/$', views.api_corpus_listing, name='api_corpus_listing'),

    url(r'^api/leaderboard/$', views.api_leaderboard, name='api_leaderboard'),

    # These are all test interfaces.
    url(r'^interface/entity/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.interface_entity, name='interface_entity'),
    url(r'^interface/entity/$', views.interface_entity, name='interface_entity'),
    url(r'^interface/relation/(?P<doc_id>[a-zA-Z_0-9.]+)/$', views.interface_relation, name='interface_relation'),
    url(r'^interface/relation/(?P<doc_id>[a-zA-Z_0-9.]+)/(?P<subject_id>[0-9]+-[0-9]+):(?P<object_id>[0-9]+-[0-9]+)/$', views.interface_relation, name='interface_relation'),
    url(r'^interface/relation/$', views.interface_relation, name='interface_relation'),
    url(r'^interface/submission/(?P<submission_id>[0-9]+)/$', views.interface_submission, name='interface_submission'),
    url(r'^interface/submission/$', views.interface_submission, name='interface_submission'),

    url(r'^$', views.home, name='home'),
]
