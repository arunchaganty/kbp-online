from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import KnowledgeBaseSubmissionForm

# Create your views here.
def home(request):
    return render(request, 'home.html')

# TODO: Save submission to database.
def process_submission(user, kb):
    # TODO: Launch a task to process this submission.
    pass

def submit(request):
    if request.method == 'POST':
        form = KnowledgeBaseSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            process_submission(request.user, form.cleaned_data['knowledge_base'])

            messages.success(request, "Submission '{}' successfully uploaded, and pending evaluation.".format(form.cleaned_data['name']))
            return redirect('home')
    else:
        form = KnowledgeBaseSubmissionForm()

    return render(request, 'submit.html', {'form': form})

def explore(request):
    # TODO: Actually implement.
    return redirect('home')
