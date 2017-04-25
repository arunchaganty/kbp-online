"""
KBPO internal models.
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from .fields import SpanField, ScoreField

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

class Sentence(models.Model):
    """
    Documents are broken up into sentences, which can be useful when displaying to turkers.
    """
    id = models.AutoField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    sentence_index = models.SmallIntegerField()
    words = ArrayField(models.TextField())
    lemmas = ArrayField(models.TextField())
    pos_tags = ArrayField(models.TextField())
    ner_tags = ArrayField(models.TextField())
    doc_char_begin = ArrayField(models.TextField())
    doc_char_end = ArrayField(models.TextField())
    gloss = models.TextField()
    dependencies = models.TextField()

    class Meta:
        managed = False
        db_table = 'sentence'
        unique_together = (('doc', 'sentence_index'),)

class SuggestedMention(models.Model):
    id = SpanField(primary_key=True)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    updated = models.DateTimeField(auto_now=True)
    sentence_id = models.ForeignKey(Sentence)
    mention_type = models.TextField()
    canonical_span = SpanField()
    gloss = models.TextField()

    class Meta:
        managed = False
        db_table = 'suggested_mention'
        unique_together = (('doc', 'id'),)

class SuggestedLink(models.Model):
    id = SpanField(primary_key=True)
    doc = models.ForeignKey('SuggestedMention', models.DO_NOTHING)
    updated = models.DateTimeField(auto_now=True)
    link_name = models.TextField()
    confidence = models.FloatField(default=1.0)

    class Meta:
        managed = False
        db_table = 'suggested_link'
        unique_together = (('doc', 'id'),)

class Submission(models.Model):
    id = models.IntegerField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)

    name = models.TextField()
    corpus_tag = models.TextField()
    details = models.TextField()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Submission: {}>".format(self.name)

    class Meta:
        managed = False
        db_table = 'submission'

class SubmissionMention(models.Model):
    submission = models.ForeignKey(Submission, models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    mention_id = SpanField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)

    canonical_id = SpanField()
    mention_type = models.TextField()
    gloss = models.TextField()

    def __str__(self):
        return self.gloss

    def __repr__(self):
        return "<Mention: {} @ {}>".format(self.gloss, self.mention_id)

    class Meta:
        managed = False
        db_table = 'submission_mention'
        unique_together = (('submission', 'doc', 'mention_id'),)

class SubmissionLink(models.Model):
    submission = models.ForeignKey(Submission, models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    mention_id = SpanField(primary_key=True)
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
        unique_together = (('submission', 'doc', 'mention_id'),)

class SubmissionRelation(models.Model):
    submission = models.ForeignKey(Submission, models.DO_NOTHING)
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    subject_id = SpanField(primary_key=True)
    object_id = SpanField(primary_key=True)
    updated = models.DateTimeField(auto_now=True)

    relation = models.TextField()
    subject_gloss = models.TextField()
    object_gloss = models.TextField()
    confidence = models.FloatField()

    def __str__(self):
        return "{} {} {}".format(self.subject_id, self.relation, self.object_id)

    def __repr__(self):
        return "<Relation: {} {} {}>".format(self.subject_id, self.relation, self.object_id)

    class Meta:
        managed = False
        db_table = 'submission_relation'
        unique_together = (('submission', 'doc', 'subject_id', 'object_id'),)

class SubmissionScore(models.Model):
    submission = models.OneToOneField(Submission, models.DO_NOTHING)
    updated = models.DateTimeField(auto_now=True)

    score_type = models.TextField()
    score = ScoreField()

    class Meta:
        managed = False
        db_table = 'submission_score'
        unique_together = (('submission', 'score_type'),)

# == Evaluation batch and question

class EvaluationBatch(models.Model):
    created = models.DateTimeField(auto_now=True)
    batch_type = models.TextField()
    params = models.TextField()
    description = models.TextField()
    corpus_tag = models.TextField()

    class Meta:
        managed = False
        db_table = 'evaluation_batch'

class EvaluationQuestion(models.Model):
    id = models.TextField()
    batch = models.ForeignKey(EvaluationBatch, models.DO_NOTHING, primary_key=True)
    created = models.DateTimeField(auto_now=True)
    params = models.TextField()

    class Meta:
        managed = False
        db_table = 'evaluation_question'
        unique_together = (('batch', 'id'),)

class MturkAssignment(models.Model):
    id = models.TextField(primary_key=True)
    batch = models.ForeignKey('MturkHit', models.DO_NOTHING)
    hit_id = models.TextField()
    created = models.DateTimeField(auto_now=True)
    worker_id = models.TextField()
    worker_time = models.IntegerField()
    status = models.TextField()
    response = models.TextField()
    ignored = models.BooleanField()
    comments = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mturk_assignment'

class MturkBatch(models.Model):
    created = models.DateTimeField(auto_now=True)
    params = models.TextField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mturk_batch'

class MturkHit(models.Model):
    id = models.TextField()
    batch = models.ForeignKey(MturkBatch, models.DO_NOTHING, primary_key=True)
    question_batch = models.ForeignKey(EvaluationQuestion, models.DO_NOTHING)
    question_id = models.TextField()
    created = models.DateTimeField(auto_now=True)
    type_id = models.TextField(blank=True, null=True)
    price = models.FloatField(blank=True, null=True)
    units = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mturk_hit'
        unique_together = (('batch', 'id'),)

# == Response tables

class EvaluationLink(models.Model):
    question_batch = models.ForeignKey('EvaluationQuestion', models.DO_NOTHING)
    question_id = models.TextField()
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    mention_id = SpanField()
    created = models.DateTimeField(auto_now=True)
    link_name = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_link'
        unique_together = (('doc', 'mention_id'),)

class EvaluationLinkResponse(models.Model):
    assignment = models.ForeignKey('MturkAssignment', models.DO_NOTHING)
    question_batch = models.ForeignKey('EvaluationQuestion', models.DO_NOTHING)
    question_id = models.TextField()
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    mention_id = SpanField()
    created = models.DateTimeField(auto_now=True)
    link_name = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_link_response'
        unique_together = (('doc', 'assignment', 'mention_id'),)

class EvaluationMention(models.Model):
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    mention_id = SpanField()
    created = models.DateTimeField(auto_now=True)
    canonical_id = SpanField()
    mention_type = models.TextField()
    gloss = models.TextField(blank=True, null=True)
    weight = models.FloatField()
    question_id = models.TextField(blank=True, null=True)
    question_batch_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_mention'
        unique_together = (('doc', 'mention_id'),)

class EvaluationMentionResponse(models.Model):
    assignment = models.ForeignKey('MturkAssignment', models.DO_NOTHING)
    question_batch = models.ForeignKey('EvaluationQuestion', models.DO_NOTHING)
    question_id = models.TextField()
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    mention_id = SpanField()
    created = models.DateTimeField(auto_now=True)
    canonical_id = SpanField()
    mention_type = models.TextField()
    gloss = models.TextField(blank=True, null=True)
    weight = models.FloatField()

    class Meta:
        managed = False
        db_table = 'evaluation_mention_response'
        unique_together = (('doc', 'assignment', 'mention_id'),)

class EvaluationRelation(models.Model):
    doc = models.ForeignKey(Document, models.DO_NOTHING)
    subject_id = SpanField()
    object_id = SpanField()
    created = models.DateTimeField(auto_now=True)
    relation = models.TextField()
    weight = models.FloatField(blank=True, null=True)
    question_id = models.TextField(primary_key=True)
    question_batch_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'evaluation_relation'
        unique_together = (('question_id', 'question_batch_id', 'doc', 'subject_id', 'object_id'),)

class EvaluationRelationResponse(models.Model):
    assignment = models.ForeignKey('MturkAssignment', models.DO_NOTHING)
    question_batch = models.ForeignKey(EvaluationQuestion, models.DO_NOTHING)
    question_id = models.TextField()
    doc = models.ForeignKey(Document, models.DO_NOTHING, primary_key=True)
    subject_id = SpanField()
    object_id = SpanField()
    created = models.DateTimeField(auto_now=True)
    relation = models.TextField()
    weight = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluation_relation_response'
        unique_together = (('doc', 'assignment', 'subject_id', 'object_id'),)
