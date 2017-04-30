from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import KnowledgeBaseSubmissionForm
from .models import SubmissionUser, SubmissionState, Document
from .tasks import process_submission

# Create your views here.
def home(request):
    return render(request, 'home.html')

def submit(request):
    if request.method == 'POST':
        form = KnowledgeBaseSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save()
            SubmissionUser(user=request.user, submission=submission).save()
            SubmissionState(submission=submission).save()

            process_submission.delay(submission.id)

            messages.success(request, "Submission '{}' successfully uploaded, and pending evaluation.".format(form.cleaned_data['name']))
            return redirect('home')
    else:
        form = KnowledgeBaseSubmissionForm()

    return render(request, 'submit.html', {'form': form})

def explore(request):
    """
    Explore a document in the corpus -- this entirely uses the
    kbpo.interface functions.
    """
    return render(request, 'explore.html')
