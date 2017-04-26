import csv
import gzip
import logging

from django import forms
from registration.forms import RegistrationForm

from kbpo.entry import validate
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
    knowledge_base = forms.FileField(help_text="The file to be uploaded. Please ensure that it is gzipped.")
    class Meta:
        model = Submission
        fields = ['name', 'details', 'corpus_tag',]
        widgets = {
            'name': forms.TextInput(),
            'corpus_tag': forms.Select(choices=(('kbp2016','KBP 2016 corpus'),)),
            }

    MAX_SIZE = 20 * 1024 * 1024 # 20 MB

    def clean_knowledge_base(self):
        data = self.cleaned_data['knowledge_base']
        if 'gzip' not in data.content_type:
            raise forms.ValidationError("Received a file with Content-Type: {}; please ensure the file is properly gzipped". format(data.content_type))

        if data.size > self.MAX_SIZE: # 20MB file.
            raise forms.ValidationError("Submitted file is larger than our current file size limit of {}MB. Please ensure that you are submitted the correct file, if not contact us at {}".format(int(self.MAX_SIZE / 1024 / 1024), ""))

        try:
            # Check that the file is gzipped.
            with gzip.open(data, 'rt') as f:
                # Check that it has the right format, aka validate it.
                data = validate(f)
                # TODO: Save validation errors in a better format and display them.
        except OSError as e:
            raise forms.ValidationError("Could not read the submitted file: {}".format(e))

        return data

    def save(self, commit=True):
        instance = super(KnowledgeBaseSubmissionForm, self).save(commit=commit)

        try:
            data = self.cleaned_data['knowledge_base']
            with gzip.open(instance.uploaded_filename, 'wt') as f:
                data.to_stream(csv.writer(f, delimiter='\t'))
        except OSError as e:
            logger.exception(e)
            instance.delete()
        return instance
