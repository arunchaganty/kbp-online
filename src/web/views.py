from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

import kbpo.interface as api

from .forms import KnowledgeBaseSubmissionForm
from .models import Submission, SubmissionUser, SubmissionState
from .models import Document
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

def explore(request, doc_id=None):
    """
    Explore a document in the corpus -- this entirely uses the
    kbpo.interface functions.
    """
    if doc_id is None:
        doc = Document.objects.order_by('?').first()
        return redirect('explore', doc_id=doc.id)
    doc = get_object_or_404(Document, id=doc_id)
    return render(request, 'explore.html', {'doc_id': doc.id})

### Interface functions
def _parse_span(doc_id, span_str):
    beg, end = span_str.split('-')
    return (doc_id, beg, end)

def interface(request, task, doc_id, subject_id=None, object_id=None):
    doc = get_object_or_404(Document, id=doc_id)

    if task == "entity":
        return render(request, 'interface_entity.html', {'doc_id': doc.id})
    elif task == "relation":
        if subject_id is not None and object_id is not None:
            # Exhaustive relations
            subject_id = _parse_span(doc.id, subject_id)
            object_id = _parse_span(doc.id, object_id)
            verify_links = True
        else:
            subject_id, object_id = None, None
            verify_links = False

        return render(request, 'interface_relation.html', {
            'doc_id': doc.id,
            'subject_id': subject_id,
            'object_id': object_id,
            'verify_links': verify_links,
            })

### API functions
def api_document(_, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    ret = api.get_document(doc.id)
    return JsonResponse(ret)

def api_suggested_mentions(_, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    ret = api.get_suggested_mentions(doc.id)
    # see https://docs.djangoproject.com/en/1.11/ref/request-response/#jsonresponse-objects
    return JsonResponse(ret, safe=False)

def api_suggested_mention_pairs(_, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    ret = api.get_suggested_mention_pairs(doc.id)
    return JsonResponse(ret)

def api_submission_mentions(_, doc_id, submission_id):
    doc = get_object_or_404(Document, id=doc_id)
    submission = get_object_or_404(Submission, id=submission_id)
    ret = api.get_submission_mentions(doc.id, submission.id)
    return JsonResponse(ret)
