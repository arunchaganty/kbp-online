"""
Celery tasks
"""
import gzip
import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from kbpo.entry import validate, upload_submission
from web.models import Submission, SubmissionState
from kbpo.evaluation_api import get_updated_scores, update_score

logger = logging.getLogger(__name__)

@shared_task
def process_submission(submission_id):
    """
    Handles the uploading of a submission.
    """
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)

    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    if state.status != 'pending-upload':
        logger.warning("Trying to process submission %s, but state is %s", submission, state.status)
        return

    try:
        with gzip.open(submission.uploaded_filename, 'rt') as f:
            mfile = validate(f)
        upload_submission(submission_id, mfile)

        # Update state of submission.
        state.status = 'pending-sampling'
        state.save()
        sample_submission.delay(submission_id)
    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()

@shared_task
def sample_submission(submission_id):
    """
    Takes care of sampling from a submission to create evaluation_question and evaluation_batch.
    """
    pass

@shared_task
def process_response(assignment_id):
    """
    Processes an mturk response.
    """
    pass

@shared_task
def score_submission(submission_id):
    """
    Updates scores of all submissions
    """
    try:
        submission = Submission.objects.get(id=submission_id)
        state = SubmissionState.objects.get(submission_id=submission_id)
    except ObjectDoesNotExist:
        return

    try:
        for (submission_id, score_type), metric in get_updated_scores(submission.corpus_tag):
            update_score(submission_id, score_type, metric)
        state.status = "done"
        state.save()
    except Exception as e:
        state.status = "error"
        state.message = e
        state.save()
