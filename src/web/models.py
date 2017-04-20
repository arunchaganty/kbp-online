from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from .fields import SpanField, ScoreField

# Defining a user for submissions.
class User(AbstractUser):
    affiliation = models.CharField(max_length=256, help_text="Your affiliation (university or company name)")
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'affiliation', 'email',]

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
    submission = models.ForeignKey(Submission, primary_key=True)
    doc_id = models.TextField(primary_key=True)
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

class SubmissionLink(models.Model):
    submission = models.ForeignKey(Submission, primary_key=True)
    doc_id = models.TextField(primary_key=True) # This is mostly a red herring. No primary key field of this sort actually exists.
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

class SubmissionRelation(models.Model):
    submission = models.ForeignKey(Submission, primary_key=True)
    doc_id = models.TextField(primary_key=True)
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

class SubmissionScore(models.Model):
    submission = models.ForeignKey(Submission, primary_key=True)
    updated = models.DateTimeField(auto_now=True)

    score_type = models.TextField()
    score = ScoreField()

    class Meta:
        managed = False
        db_table = 'submission_score'
