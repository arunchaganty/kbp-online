"""
KBPO internal models.
"""
import os

from django.core.files import File
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.contrib.postgres.search import SearchVector

from kbpo import api

from .fields import SpanField, ScoreField

CORPUS_NAMES = {
    "kbp2014": "TAC-KBP 2014 corpus",
    "kbp2015": "TAC-KBP 2015 corpus",
    "kbp2016": "TAC-KBP 2016 corpus",
    }

## Corpus
class CorpusState(models.Model):
    corpus_tag = models.TextField()
    state = models.TextField()

    class Meta:
        managed = False
        db_table = 'corpus_state'

class Document(models.Model):
    id = models.TextField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    title = models.TextField(blank=True, null=True)
    doc_date = models.DateField(blank=True, null=True)
    doc_length = models.IntegerField(blank=True, null=True)
    doc_digest = models.TextField(blank=True, null=True)
    gloss = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'document'

class DocumentTag(models.Model):
    doc = models.OneToOneField(Document, primary_key=True)
    tag = models.TextField()

    class Meta:
        managed = False
        db_table = 'document_tag'
        unique_together = (('doc', 'tag'),)

class DocumentIndex(models.Model):
    doc_id = models.TextField(blank=True, null=True)
    tsvector = SearchVector(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'document_index'

class Sentence(models.Model):
    """
    Documents are broken up into sentences, which can be useful when displaying to turkers.
    """
    id = models.AutoField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    span = SpanField()
    sentence_index = models.SmallIntegerField()
    gloss = models.TextField()
    token_spans = ArrayField(SpanField())
    words = ArrayField(models.TextField())
    lemmas = ArrayField(models.TextField())
    pos_tags = ArrayField(models.TextField())
    ner_tags = ArrayField(models.TextField())
    dependencies = models.TextField()

    class Meta:
        managed = False
        db_table = 'sentence'
        unique_together = (('doc', 'span'),)

class SuggestedMention(models.Model):
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    span = SpanField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    sentence_id = models.ForeignKey(Sentence)
    mention_type = models.TextField()
    canonical_span = SpanField()
    gloss = models.TextField()

    class Meta:
        managed = False
        db_table = 'suggested_mention'
        unique_together = (('doc', 'span'),)

class SuggestedLink(models.Model):
    doc = models.ForeignKey('SuggestedMention', models.DO_NOTHING)
    span = SpanField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    link_name = models.TextField()
    confidence = models.FloatField(default=1.0)

    class Meta:
        managed = False
        db_table = 'suggested_link'
        unique_together = (('doc', 'span'),)

## Submission
#- modified -v
class Submission(models.Model):
    id = models.AutoField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)

    name = models.TextField()
    corpus_tag = models.TextField(verbose_name='Document corpus')
    details = models.TextField()
    active = models.BooleanField(default=True)

    objects = models.Manager()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Submission: {}>".format(self.name)

    class Meta:
        managed = False
        db_table = 'submission'

    @property
    def corpus_name(self):
        return CORPUS_NAMES.get(self.corpus_tag, self.corpus_tag)

    @property
    def log_file(self):
        if os.path.exists(self.log_filename):
            return File(open(self.log_filename))
        else:
            return None

    @property
    def log_filename(self):
        """
        Load the uploaded filename from the server.
        """
        return os.path.join(settings.MEDIA_ROOT, 'submissions', '{}.m.log.gz'.format(self.id))

    @property
    def uploaded_file(self):
        if os.path.exists(self.uploaded_filename):
            return File(open(self.uploaded_filename))
        else:
            return None

    @property
    def uploaded_filename(self):
        """
        Load the uploaded filename from the server.
        """
        return os.path.join(settings.MEDIA_ROOT, 'submissions', '{}.m.gz'.format(self.id))

    @property
    def original_file(self):
        if os.path.exists(self.original_filename):
            return File(open(self.original_filename))
        else:
            return None

    @property
    def original_filename(self):
        """
        Load the uploaded filename from the server.
        """
        return os.path.join(settings.MEDIA_ROOT, 'submissions', '{}.original.gz'.format(self.id))

class SubmissionMention(models.Model):
    submission = models.ForeignKey(Submission, models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    span = SpanField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    canonical_span = SpanField()
    mention_type = models.TextField()
    gloss = models.TextField()

    def __str__(self):
        return self.gloss

    def __repr__(self):
        return "<Mention: {} @ {}>".format(self.gloss, self.mention_id)

    class Meta:
        managed = False
        db_table = 'submission_mention'
        unique_together = (('submission', 'doc', 'span'),)

class SubmissionLink(models.Model):
    submission = models.ForeignKey(Submission, models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    span = SpanField()
    updated = models.DateTimeField(auto_now=True)
    link_name = models.TextField()
    confidence = models.FloatField()

    def __str__(self):
        return self.link_name

    def __repr__(self):
        return "<Link: {} @ {}>".format(self.link_name, self.mention_id)

    class Meta:
        managed = False
        db_table = 'submission_link'
        unique_together = (('submission', 'doc', 'span'),)

class SubmissionRelation(models.Model):
    submission = models.ForeignKey(Submission, models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    subject = SpanField(primary_key=True)
    object = SpanField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    relation = models.TextField()
    provenances = ArrayField(SpanField())
    confidence = models.FloatField()

    def __str__(self):
        return "{} {} {}".format(self.subject_id, self.relation, self.object_id)

    def __repr__(self):
        return "<Relation: {} {} {}>".format(self.subject_id, self.relation, self.object_id)

    class Meta:
        managed = False
        db_table = 'submission_relation'
        unique_together = (('submission', 'doc', 'subject', 'object'),)

class SubmissionScore(models.Model):
    submission = models.OneToOneField(Submission, models.DO_NOTHING)
    updated = models.DateTimeField(auto_now=True)
    score_type = models.TextField()
    score = ScoreField()
    left_interval = ScoreField()
    right_interval = ScoreField()

    class Meta:
        managed = False
        db_table = 'submission_score'

# == Evaluation batch and question
class EvaluationBatch(models.Model):
    id = models.IntegerField(primary_key=True)
    created = models.DateTimeField(auto_now=True)
    batch_type = models.TextField(choices=[
        ('exhaustive_entities', 'Exhaustive entities'),
        ('exhaustive_relations', 'Exhaustive relations'),
        ('selective_relations', 'Selective relations'),
        ])
    corpus_tag = models.TextField()
    description = models.TextField()

    class Meta:
        managed = False
        db_table = 'evaluation_batch'

    @property
    def status(self):
        r"""
        Checks the status of an evaluation batch, which is simply the
        state of all its children
        """
        return api.get_evaluation_batch_status(self.id)

    def __repr__(self):
        return "<EvaluationBatch: {} on {}>".format(self.batch_type, self.corpus_tag)

    def __str__(self):
        return "EvaluationBatch {}".format(self.created)

class EvaluationQuestion(models.Model):
    CHOICES = [
        ('pending-turking', 'Uploading to Amazon Mechanical Turk'),
        ('pending-annotation', 'Crowdsourcing'),
        ('pending-verification', 'Verifying annotations'),
        ('pending-aggregation', 'Aggregating annotations'), # Note, we might combine the above two step.
        ('done', 'Done'),
        ('revoked', 'Revoked'),
        ('error', 'Error'),
        ]
    id = models.TextField(primary_key=True)
    batch = models.ForeignKey(EvaluationBatch, models.DO_NOTHING, related_name='questions')
    created = models.DateTimeField(auto_now=True)
    params = models.TextField()
    state = models.TextField(choices=CHOICES)
    message = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_question'
        unique_together = (('batch', 'id'),)

class MturkBatch(models.Model):
    created = models.DateTimeField(auto_now=True)
    params = JSONField()
    description = models.TextField(blank=True, null=True)

    def __repr__(self):
        return "<MTurkBatch {}>".format(self.id)

    def __str__(self):
        return "MTurkBatch {}".format(self.id)

    class Meta:
        managed = False
        db_table = 'mturk_batch'

class MturkHit(models.Model):
    CHOICES = [
        ('pending-annotation', 'Crowdsourcing'),
        ('pending-aggregation', 'Aggregating'),
        ('done', 'Done'),
        ('revoked', 'Revoked'),
        ('error', 'Error'),
        ]
    id = models.TextField(primary_key=True)
    batch = models.ForeignKey(MturkBatch, models.DO_NOTHING)
    question_batch = models.ForeignKey(EvaluationBatch, models.DO_NOTHING)
    question = models.ForeignKey(EvaluationQuestion, models.DO_NOTHING)
    created = models.DateTimeField(auto_now=True)
    type_id = models.TextField(blank=True, null=True)
    price = models.FloatField(blank=True, null=True)
    units = models.IntegerField(blank=True, null=True)
    max_assignments = models.IntegerField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)

    def __repr__(self):
        return "<MTurkHIT {}>".format(self.id)

    def __str__(self):
        return "MTurkHIT {}".format(self.id)


    class Meta:
        managed = False
        db_table = 'mturk_hit'
        unique_together = (('batch', 'id'),)

class MturkAssignment(models.Model):
    CHOICES = [
        ('pending-extraction', 'Extracting'),
        ('pending-validation', 'Validating'),
        ('pending-payment', 'Paying'),
        ('pending-rejection-verification', 'Verifying Rejection'),
        ('verified-rejection', 'Paying'),
        ('pending-payment', 'Verifying Rejection'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('error', 'Error'),
        ]
    id = models.TextField(primary_key=True)
    batch = models.ForeignKey(MturkBatch, models.DO_NOTHING)
    hit = models.ForeignKey(MturkHit, models.DO_NOTHING)
    created = models.DateTimeField(auto_now=True)
    worker_id = models.TextField()
    worker_time = models.IntegerField()
    response = JSONField()
    ignored = models.BooleanField()
    verified = models.NullBooleanField()
    comments = models.TextField(blank=True, null=True)
    state = models.TextField(choices=CHOICES)
    message = models.TextField()

    def __repr__(self):
        return "<MTurkAssignment {}>".format(self.id)

    def __str__(self):
        return "MTurkAssignment {}".format(self.id)

    class Meta:
        managed = False
        db_table = 'mturk_assignment'

# == Response tables
class EvaluationLink(models.Model):
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    span = SpanField()
    created = models.DateTimeField(auto_now=True)
    question_batch = models.ForeignKey('EvaluationQuestion', models.DO_NOTHING)
    question_id = models.TextField() # Not linking to question because question needs (question_id, batch_id)
    link_name = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_link'
        unique_together = (('doc', 'span'),)

class EvaluationLinkResponse(models.Model):
    assignment = models.ForeignKey('MturkAssignment', models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    span = SpanField()
    created = models.DateTimeField(auto_now=True)
    question_batch = models.ForeignKey('EvaluationBatch', models.DO_NOTHING)
    question_id = models.TextField()
    link_name = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_link_response'
        unique_together = (('assignment', 'doc', 'span'),)

class EvaluationMention(models.Model):
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    span = SpanField()
    created = models.DateTimeField(auto_now=True)
    question_id = models.TextField(blank=True, null=True)
    question_batch_id = models.IntegerField(blank=True, null=True)
    canonical_span = SpanField()
    mention_type = models.TextField()
    gloss = models.TextField(blank=True, null=True)
    weight = models.FloatField()

    class Meta:
        managed = False
        db_table = 'evaluation_mention'
        unique_together = (('doc', 'span'),)

class EvaluationMentionResponse(models.Model):
    assignment = models.ForeignKey('MturkAssignment', models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    span = SpanField()
    created = models.DateTimeField(auto_now=True)
    question_batch = models.ForeignKey('EvaluationBatch', models.DO_NOTHING)
    question_id = models.TextField()
    canonical_span = SpanField()
    mention_type = models.TextField()
    gloss = models.TextField(blank=True, null=True)
    weight = models.FloatField()

    class Meta:
        managed = False
        db_table = 'evaluation_mention_response'
        unique_together = (('assignment', 'doc', 'span'),)

class EvaluationRelation(models.Model):
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    subject = SpanField()
    object = SpanField()
    created = models.DateTimeField(auto_now=True)
    question_batch_id = models.IntegerField()
    question_id = models.TextField(primary_key=True)
    relation = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_relation'
        unique_together = (('doc', 'subject', 'object'),)

class EvaluationRelationResponse(models.Model):
    assignment = models.ForeignKey('MturkAssignment', models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    subject = SpanField()
    object = SpanField()
    created = models.DateTimeField(auto_now=True)
    question_batch = models.ForeignKey(EvaluationBatch, models.DO_NOTHING)
    question_id = models.TextField()
    relation = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_relation_response'
        unique_together = (('assignment', 'object', 'doc', 'subject'),)

## Sampling
class SampleBatch(models.Model):
    created = models.DateTimeField(auto_now=True)
    submission = models.ForeignKey('Submission', models.DO_NOTHING, blank=True, null=True, related_name="sample_batches")
    distribution_type = models.TextField()
    corpus_tag = models.TextField()
    params = JSONField()

    class Meta:
        managed = False
        db_table = 'sample_batch'

class DocumentSample(models.Model):
    batch = models.ForeignKey('SampleBatch', models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'document_sample'
        unique_together = (('doc', 'batch'),)

class SubmissionSample(models.Model):
    batch = models.ForeignKey(SampleBatch, models.DO_NOTHING)
    submission = models.ForeignKey(Submission, models.DO_NOTHING, primary_key=True, related_name='samples')
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    subject = SpanField()
    object = SpanField()
    created = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'submission_sample'
        unique_together = (('submission', 'doc', 'subject', 'object', 'batch'),)
