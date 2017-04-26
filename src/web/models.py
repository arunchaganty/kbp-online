from django.db import models
from django.contrib.auth.models import AbstractUser
from .kbpo_models import Document, DocumentTag, Submission

# Defining a user for submissions.
class User(AbstractUser):
    affiliation = models.CharField(max_length=256, help_text="Your affiliation (university or company name)")
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'affiliation', 'email',]

class SubmissionUser(models.Model):
    submission = models.OneToOneField(Submission, primary_key=True)
    user = models.ForeignKey(User)

class SubmissionState(models.Model):
    submission = models.OneToOneField(Submission, primary_key=True)
    status = models.TextField(default='pending-upload')
    message = models.TextField(blank=True, default='')

    objects = models.Manager()

    def __str__(self):
        return "<SubmissionState {}: {}>".format(self.submission_id, self.status)
