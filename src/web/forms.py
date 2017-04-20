from django import forms
from registration.forms import RegistrationForm
from .models import User
import gzip
from kbpo.entry import validate

class UserForm(RegistrationForm):
    class Meta:
        model = User
        fields = ["first_name","last_name", "affiliation", "username", "email"]

class KnowledgeBaseSubmissionForm(forms.Form):
    """
    A knowledge base submitted by the user.
    """
    name = forms.CharField(max_length=120, help_text="A short identifier for this submission")
    description = forms.CharField(max_length=200, help_text="A short description of the techniques used for this submission")
    knowledge_base = forms.FileField(help_text="The file to be uploaded. Please ensure that it is gzipped.")

    MAX_SIZE = 20 * 1024 * 1024 # 20 MB

    def clean_knowledge_base(self):
        data = self.cleaned_data['knowledge_base']
        if data.content_type != 'application/x-gzip':
            raise forms.ValidationError("Received a file with Content-Type: {}; please ensure the file is properly gzipped". format(data.content_type))

        if data.size > self.MAX_SIZE: # 20MB file.
            raise forms.ValidationError("Submitted file is larger than our current file size limit of {}MB. Please ensure that you are submitted the correct file, if not contact us at {}".format(int(self.MAX_SIZE / 1024 / 1024), ""))

        try:
            # Check that the file is gzipped.
            with gzip.open(data, 'rt') as f:
                # Check that it has the right format, aka validate it.
                data = validate(f)
        except OSError as e:
            raise forms.ValidationError("Could not read the submitted file: {}".format(e))

        return data
