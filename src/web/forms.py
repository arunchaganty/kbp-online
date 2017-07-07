import csv
import gzip
import logging

import pdb
from django import forms
from registration.forms import RegistrationForm

from kbpo import db
from .models import User, Submission

logger = logging.getLogger(__name__)

class UserForm(RegistrationForm):
    class Meta:
        model = User
        fields = ["first_name","last_name", "affiliation", "username", "email"]

class KnowledgeBaseSubmissionForm(forms.ModelForm):
    """
    A knowledge base submitted by the user.
    """
    file_format = forms.ChoiceField(choices=[("tackb2016", "TAC-KBP KB format (2015--2016)"), ("mfile", "Mention-based KB format")], help_text="")
    knowledge_base = forms.FileField(help_text="The file to be uploaded. Please ensure that it is gzipped.")

    class Meta:
        model = Submission
        fields = ['name', 'details', 'corpus_tag',]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'A short identifying description of your system (e.g. "Selective Attention Neural Network")'}),
            'details': forms.Textarea(attrs={'placeholder': 'A brief description of what identifies this model or iteration.', 'rows': 4}),
            'corpus_tag': forms.Select(choices=(('kbp2016','KBP 2016 corpus'),)),
            }

    MAX_SIZE = 50 * 1024 * 1024 # 50 MB
    CHUNK_SIZE = 1024*1024

    def clean_knowledge_base(self):

        data = self.cleaned_data['knowledge_base']

        if 'gzip' not in data.content_type:
            raise forms.ValidationError("Received a file with unsupported Content-Type ({}); please ensure the file is properly gzipped". format(data.content_type))

        if data.size > self.MAX_SIZE: # 20MB file.
            raise forms.ValidationError("Submitted file is larger than our current file size limit of {}MB. Please ensure that you are submitted the correct file, if not contact us at {}".format(int(self.MAX_SIZE / 1024 / 1024), ""))

        try:
            # Check that the file is gzipped.
            # Try to read the whole file as a way to ensure that it is a valid zip file.
            with gzip.open(data.temporary_file_path(), 'rt', encoding='utf-8') as f:
                buf = f.read(self.CHUNK_SIZE)
                while len(buf) > 0:
                    buf = f.read(self.CHUNK_SIZE)
        except OSError as e:
            raise forms.ValidationError("Could not read the submitted file: {}".format(e))

        self.cleaned_data['knowledge_base'] = data
        return data

    def save(self, commit=True):
        instance = super(KnowledgeBaseSubmissionForm, self).save(commit=commit)

        try:
            data = self.cleaned_data['knowledge_base']
            with gzip.open(data.temporary_file_path(), 'rt', encoding='utf-8') as f, gzip.open(instance.original_filename, 'wt', encoding='utf-8') as g:
                buf = f.read(self.CHUNK_SIZE)
                while len(buf) > 0:
                    g.write(buf)
                    buf = f.read(self.CHUNK_SIZE)

        except (AttributeError, OSError)  as e:
            logger.exception(e)
            instance.delete()
        return instance
