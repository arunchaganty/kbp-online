from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

# Defining a user for submissions.
class User(AbstractUser):
    affiliation = models.CharField(max_length=256, help_text="Your affiliation (university or company name)")
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'affiliation', 'email',]