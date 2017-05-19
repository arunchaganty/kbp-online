import json
import logging
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.contrib import messages

from kbpo import api

from .forms import KnowledgeBaseSubmissionForm
from .models import Submission, SubmissionUser, SubmissionState
from .models import Document
from .tasks import process_submission

logger = logging.getLogger(__name__)

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
def _parse_span(span_str):
    if "-" not in span_str: return None
    beg, end = span_str.split('-', 1)
    if not beg.isdigit() or not end.isdigit(): return None
    return (int(beg), int(end))

def interface(request, task, doc_id, subject_id=None, object_id=None):
    if subject_id is not None or object_id is not None:
        subject_id, object_id = _parse_span(subject_id), _parse_span(object_id)
        if subject_id is None or object_id is None:
            raise Http404("Invalid mention spans: {}:{}".format(subject_id, object_id))

    doc = get_object_or_404(Document, id=doc_id)

    if task == "entity":
        if request.method == 'POST': # handle response.
            response = request.POST["response"].strip().replace("\xa0", " ") # these null space strings are somehow always introduced
            response = json.loads(response)
            logger.info("Received response: %s", response)

        return render(request, 'interface_entity.html', {
            'doc_id': doc.id,
            'assignment_id': "TEST_ASSIGNMENT",
            'hit_id': "TEST_HIT",
            'worker_id': "TEST_WORKER",
            })
    elif task == "relation":
        if request.method == 'POST': # handle response.
            response = request.POST["response"].strip().replace("\xa0", " ") # these null space strings are somehow always introduced
            response = json.loads(response)
            logger.info("Received response: %s", response)

        if subject_id is not None and object_id is not None:
            # Exhaustive relations
            mention_pair = "{}-{}:{}-{}".format(subject_id[0], subject_id[1], object_id[0], object_id[1])
            verify_links = True
        else:
            mention_pair = ""
            verify_links = False

        return render(request, 'interface_relation.html', {
            'assignment_id': "TEST_ASSIGNMENT",
            'hit_id': "TEST_HIT",
            'worker_id': "TEST_WORKER",
            'doc_id': doc.id,
            'mention_pair': mention_pair,
            'verify_links': verify_links,
            })

def do_task(request):
    """
    Dispatches a turker task based on hitId, workerId, assignmentId
    specified in the GET parameters
    """
    if not request.GET or "hitId" not in request.GET:
        hit_id = next(api.get_hits(1)).id
        return HttpResponseRedirect(reverse('do_task') + '?' + urlencode({
            "assignmentId": "TEST_ASSIGNMENT",
            "hitId": hit_id,
            "workerId": "TEST_WORKER",
            }))
    else:
        hit_id = request.GET["hitId"]
        try:
            params = api.get_task_params(hit_id)
        except StopIteration:
            raise Http404("HIT {} does not exist".format(hit_id))

        if request.POST:
            response = request.POST["response"].strip().replace("\xa0", " ") # these null space strings are somehow always introduced
            response = json.loads(response)

            api.insert_assignment(
                assignment_id=request.POST["assignmentId"],
                hit_id=request.POST["hitId"],
                worker_id=request.POST["workerId"],
                worker_time=request.POST["workerTime"],
                comments=request.POST["comments"],
                response=response)
            return JsonResponse({"success": True})
        # Get the corresponding mturk_hit and evaluation_question to
        # render this
        doc = get_object_or_404(Document, id=params["doc_id"])

        if params["batch_type"] == "exhaustive_entities":
            return render(request, 'interface_entity.html', {
                'doc_id': doc.id,
                'assignment_id': request.GET["assignmentId"],
                'hit_id': request.GET["hitId"],
                'worker_id': request.GET["workerId"],
                })
        elif params["batch_type"] == "exhaustive_relations":
            return render(request, 'interface_relation.html', {
                'doc_id': doc.id,
                'assignment_id': request.GET["assignmentId"],
                'hit_id': request.GET["hitId"],
                'worker_id': request.GET["workerId"],
                })
        elif params["batch_type"] == "selective_relations":
            return render(request, 'interface_relation.html', {
                'doc_id': doc.id,
                'subject_id': params["mention_1"],
                'object_id': params["mention_2"],
                'assignment_id': request.GET["assignmentId"],
                'hit_id': request.GET["hitId"],
                'worker_id': request.GET["workerId"],
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

def api_suggested_mention_pairs(_, doc_id, subject_id=None, object_id=None):
    if subject_id is not None or object_id is not None:
        subject_id, object_id = _parse_span(subject_id), _parse_span(object_id)
        if subject_id is None or object_id is None:
            raise Http404("Invalid mention spans: {}:{}".format(subject_id, object_id))
    doc = get_object_or_404(Document, id=doc_id)

    # Get the basic mentions
    mentions = api.get_suggested_mentions(doc.id)
    mentions = {m["span"]: m for m in mentions}

    # Get the pairs.
    if subject_id is not None and object_id is not None:
        pairs = [{"subject": subject_id, "object": object_id}]
    else:
        pairs = api.get_suggested_mention_pairs(doc.id)
    # Construct mention pairs using the above information.
    ret = [{"subject": mentions[p["subject"]], "object": mentions[p["object"]],} for p in pairs]

    return JsonResponse(ret, safe=False)

def api_submission_mentions(_, doc_id, submission_id):
    doc = get_object_or_404(Document, id=doc_id)
    submission = get_object_or_404(Submission, id=submission_id)
    ret = api.get_submission_mentions(submission.id, doc.id)
    return JsonResponse(ret, safe=False)

def api_evaluation_mentions(_, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    ret = api.get_evaluation_mentions(doc.id)
    return JsonResponse(ret, safe=False)

def api_evaluation_mention_pairs(_, doc_id, subject_id=None, object_id=None):
    if subject_id is not None or object_id is not None:
        subject_id, object_id = _parse_span(subject_id), _parse_span(object_id)
        if subject_id is None or object_id is None:
            raise Http404("Invalid mention spans: {}:{}".format(subject_id, object_id))
    doc = get_object_or_404(Document, id=doc_id)

    # Get the basic mentions
    mentions = api.get_evaluation_mentions(doc.id)
    mentions = {m["span"]: m for m in mentions}

    # Get the pairs.
    if subject_id is not None and object_id is not None:
        pairs = [{"subject": subject_id, "object": object_id}]
    else:
        pairs = api.get_evaluation_mention_pairs(doc.id)
    # Construct mention pairs using the above information.
    ret = [{"subject": mentions[p["subject"]], "object": mentions[p["object"]],} for p in pairs]

    return JsonResponse(ret, safe=False)
