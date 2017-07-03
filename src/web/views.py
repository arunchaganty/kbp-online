import os
import json
import logging
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import JsonResponse, HttpResponseRedirect, Http404, StreamingHttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings

from kbpo import api

from . import tasks
from .forms import KnowledgeBaseSubmissionForm
from .models import Submission, SubmissionUser, SubmissionState
from .models import Document, DocumentTag

logger = logging.getLogger(__name__)

# Create your views here.
def home(request):
    return render(request, 'home.html')

@login_required
def submissions_remove(request, submission_id):
    # TODO: Remove from submission_* too.
    # Check that the submission is indeed that of the user.
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.user.user != request.user:
        raise Http404("You do not have a submission with that id")
    submission.active = False
    submission.save()
    return redirect("submissions")

def stream_file(path):
    fstream = open(path, "rb")
    response = StreamingHttpResponse(fstream, content_type='application/gzip')
    response['Content-Disposition'] = 'attachment; filename={}'.format(os.path.basename(path))
    response['Content-Length'] = os.stat(path).st_size
    return response

@login_required
def submissions_download(request, submission_id, resource):
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.user.user != request.user:
        raise Http404("You do not have a submission with that id")

    if resource == "log" and os.path.exists(submission.log_filename):
        return stream_file(submission.log_filename)
    elif resource == "kb" and os.path.exists(submission.original_filename):
        return stream_file(submission.original_filename)
    elif resource == "mfile" and os.path.exists(submission.uploaded_filename):
        return stream_file(submission.uploaded_filename)
    else:
        messages.error(request, "We could not find the `{}` for submission {}. Please contact the administrators for more details and assistance.".format(resource, submission_id))
        return redirect("submissions")

@login_required
def submissions(request):
    if request.method == 'POST':
        form = KnowledgeBaseSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save()
            SubmissionUser(user=request.user, submission=submission).save()
            SubmissionState(submission=submission).save()

            tasks.validate_submission.delay(submission.id, form.cleaned_data["file_format"])

            messages.info(request, "Submission '{}' uploaded and currently being validated. Please reload this page to see the latest status.".format(form.cleaned_data['name'],))
            return redirect('submissions')
    else:
        form = KnowledgeBaseSubmissionForm()

    submissions = SubmissionUser.objects.filter(user=request.user, submission__active=True)
    return render(request, 'submit.html', {'form': form, 'submissions': submissions})

def explore_corpus(request, corpus_tag, doc_id=None):
    """
    Explore a document in the corpus -- this entirely uses the
    kbpo.interface functions.
    """
    if doc_id is None:
        # List all documents for a corpus_tag (?).
        return render(request, 'explore_corpus.html', {'corpus_tag': corpus_tag})
    doc = get_object_or_404(Document, id=doc_id)
    return render(request, 'explore_document.html', {'doc_id': doc.id})

def explore_submission(request, submission_id):
    """
    Explore a document in the corpus -- this entirely uses the
    kbpo.interface functions.
    """
    submission = get_object_or_404(Submission, id=submission_id)

    return render(request, 'explore_submission.html', {'submission': submission})

### Interface functions
def _parse_span(span_str):
    if "-" not in span_str: return None
    beg, end = span_str.split('-', 1)
    if not beg.isdigit() or not end.isdigit(): return None
    return (int(beg), int(end))

def interface_entity(request, doc_id=None):
    if request.method == 'POST': # handle response.
        response = request.POST["response"].strip().replace("\xa0", " ") # these null space strings are somehow always introduced
        response = json.loads(response)
        messages.success(request, "Thank you for trying out our task! Unfortunately, At this point, we are only using responses through Amazon Mechanical Turk.")
        redirect("home")

    if doc_id is None:
        #doc_id = DocumentTag.objects.filter(tag="kbp2016").first().doc_id
        doc_id = DocumentTag.objects.filter(tag="kbp2016").order_by('?').first().doc_id
        return redirect("interface_entity", doc_id=doc_id)
    doc = get_object_or_404(Document, id=doc_id)
    params = {
        "batch_type": "exhaustive_entities",
        "doc_id": doc.id,
        }

    return render(request, 'interface_entity.html', {
        'doc_id': doc.id,
        'params': json.dumps(params),
        'assignment_id': "TEST_ASSIGNMENT",
        'hit_id': "TEST_HIT",
        'worker_id': "TEST_WORKER",
        })

def interface_relation(request, doc_id=None, submission_id=None, subject_id=None, object_id=None):
    if request.method == 'POST': # handle response.
        response = request.POST["response"].strip().replace("\xa0", " ") # these null space strings are somehow always introduced
        response = json.loads(response)
        messages.success(request, "Thank you for trying out our task! Unfortunately, At this point, we are only using responses through Amazon Mechanical Turk.")
        return redirect("home")

    if doc_id is None:
        #doc_id = DocumentTag.objects.filter(tag="kbp2016").first().doc_id
        doc_id = DocumentTag.objects.filter(tag="kbp2016").order_by('?').first().doc_id
        # TODO: Get a doc for which we have done exhaustive_entities.

        return redirect("interface_relation", doc_id=doc_id)
    get_object_or_404(Document, id=doc_id)

    if submission_id is not None or subject_id is not None or object_id is not None:
        get_object_or_404(Submission, id=submission_id)
        subject_id, object_id = _parse_span(subject_id), _parse_span(object_id)
        if subject_id is None or object_id is None:
            raise Http404("Invalid mention spans: {}:{}".format(subject_id, object_id))

        subject, object_ = api.get_submission_mention_pair(submission_id, doc_id, subject_id, object_id)

        # Construct a params object for this task.
        params = {
            "batch_type": "selective_relations",
            "submission_id": None,
            "doc_id": doc_id,
            "subject": subject,
            "object": object_,
            }
    else:
        # Construct a params object for this task.
        params = {
            "batch_type": "exhaustive_relations",
            "doc_id": doc_id,
            }

    # Constructs a params object based on this task.
    return render(request, 'interface_relation.html', {
        'assignment_id': "TEST_ASSIGNMENT",
        'hit_id': "TEST_HIT",
        'worker_id': "TEST_WORKER",
        'doc_id': doc_id,
        'params': json.dumps(params),
        })

def interface_submission(_, submission_id=None):
    if submission_id is None:
        #submission_id = Submission.objects.order_by('?').first().id
        submission_id = 25
        #submission_id = Submission.objects.first().id
        return redirect(
            "interface_submission",
            submission_id=submission_id)
    submission = get_object_or_404(Submission, id=submission_id)

    relns = api.get_submission_relation_list(submission.id, 1)
    # Get a random relation
    reln = relns[0]

    return redirect(
        "interface_relation",
        submission_id=submission_id,
        doc_id=reln["doc_id"],
        subject_id="{}-{}".format(*reln["subject"]),
        object_id="{}-{}".format(*reln["object"]),
        )

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
        assignment_id = request.GET.get("assignmentId")
        if assignment_id is None:
            raise Http404("AssignmentId not set")

        if request.POST:
            response = request.POST["response"].strip().replace("\xa0", " ") # these null space strings are somehow always introduced
            response = json.loads(response)

            worker_id = request.POST.get("workerId")
            worker_time = request.POST.get("workerTime")
            comments = request.POST.get("comments")

            if assignment_id is None:
                return JsonResponse({"success": False, "reason": "No assignmentId"})
            elif assignment_id == "ASSIGNMENT_ID_NOT_AVAILABLE":
                return JsonResponse({"success": False, "reason": "Assignment id not available"})

            api.insert_assignment(
                assignment_id=assignment_id,
                hit_id=hit_id,
                worker_id=worker_id,
                worker_time=worker_time,
                comments=comments,
                response=response)
            tasks.process_response.delay(assignment_id)
            # Just in case someone is listening.
            return JsonResponse({"success": True})
        # Get the corresponding mturk_hit and evaluation_question to
        # render this
        doc = get_object_or_404(Document, id=params["doc_id"])

        if params["batch_type"] == "exhaustive_entities":
            return render(request, 'interface_entity.html', {
                'doc_id': doc.id,
                'params': json.dumps(params),
                'assignment_id': request.GET["assignmentId"],
                'hit_id': request.GET["hitId"],
                'worker_id': request.GET["workerId"],
                'mturk_form_target': settings.MTURK_FORM_TARGET,
                'hidenav' : True,
                })
        elif params["batch_type"] == "exhaustive_relations":
            return render(request, 'interface_relation.html', {
                'doc_id': doc.id,
                'params': json.dumps(params),
                'assignment_id': request.GET["assignmentId"],
                'hit_id': request.GET["hitId"],
                'worker_id': request.GET["workerId"],
                'mturk_form_target': settings.MTURK_FORM_TARGET,
                'hidenav' : True,
                })
        elif params["batch_type"] == "selective_relations":
            subject, object_ = tuple(params["subject"]), tuple(params["object"])
            # ordering the mention pair needs types: so fixing in js.
            #if object_ < subject:
            #    subject, object_ = object_, subject

            return render(request, 'interface_relation.html', {
                'doc_id': doc.id,
                'mention_pair': '{}-{}:{}-{}'.format(subject[0], subject[1], object_[0], object_[1]),
                'params': json.dumps(params),
                'assignment_id': request.GET["assignmentId"],
                'hit_id': request.GET["hitId"],
                'worker_id': request.GET.get("workerId"),
                'mturk_form_target': settings.MTURK_FORM_TARGET,
                'hidenav' : True,
                })

### API functions
def api_leaderboard(_):
    ret = api.get_leaderboard()
    return JsonResponse(ret)

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

def api_evaluation_relations(_, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    # Get the basic mentions
    mentions = api.get_evaluation_mentions(doc.id)
    mentions = {m["span"]: m for m in mentions}

    relations = api.get_evaluation_relations(doc.id)
    # Construct mention pairs using the above information.
    ret = [{"subject": mentions[r["subject"]],
            "object": mentions[r["object"]],
            "relation": r["relation"],} for r in relations if r["subject"] in mentions and r["object"] in mentions]

    return JsonResponse(ret, safe=False)

def api_submission_entries(_, submission_id):
    """
    Get all the submitted relations from submission_id.
    """
    ret = api.get_submission_entries(submission_id)
    return JsonResponse(ret, safe=False)

def api_corpus_listing(_, corpus_tag):
    """
    Get all the submitted relations from submission_id.
    """
    ret = api.get_corpus_listing(corpus_tag)
    return JsonResponse(ret, safe=False)
