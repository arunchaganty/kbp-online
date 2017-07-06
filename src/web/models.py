from django.db import models
from django.contrib.auth.models import AbstractUser
from .kbpo_models import Document, DocumentTag, Submission, SubmissionScore
from .kbpo_models import EvaluationBatch, EvaluationQuestion, MturkBatch, MturkHit, MturkAssignment

# Defining a user for submissions.
class User(AbstractUser):
    affiliation = models.CharField(max_length=256, help_text="Your affiliation (university or company name) which will be displayed on the leaderboard.")
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'affiliation', 'email',]

class SubmissionUser(models.Model):
    submission = models.OneToOneField(Submission, related_name="user", primary_key=True)
    user = models.ForeignKey(User)

class SubmissionState(models.Model):
    CHOICES = [
        ('error', "Error"),
        ('pending-validation', "Validating submission"),
        ('pending-upload', "Uploading into database"),
        ('pending-sampling', "Sampling instances"),
        ('pending-turking', "Uploading to Amazon Mechanical Turk"),
        ('pending-annotation', "Crowdsourcing"),
        ('pending-scoring', "Scoring"),
        ('done', "Evaluated!"),
        ]
    CHOICES_ = dict(CHOICES)

    submission = models.OneToOneField(Submission, related_name="state", primary_key=True)
    status = models.CharField(max_length=20, default='pending-validation', choices=CHOICES)
    message = models.TextField(blank=True, default='')

    objects = models.Manager()

    def __repr__(self):
        return "<SubmissionState {}: {}>".format(self.submission_id, self.status)

    def __str__(self):
        return self.CHOICES_.get(self.status, self.status)
