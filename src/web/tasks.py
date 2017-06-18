"""
Celery tasks
"""
import gzip
import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from service.settings import MTURK_TARGET

from kbpo import db
from kbpo import api
from kbpo.parser import MFileReader
from kbpo.evaluation_api import get_updated_scores, update_score
from kbpo.sampling import sample_submission as _sample_submission
from kbpo.questions import create_evaluation_batch_from_submission_sample
from kbpo.turk import connect, create_batch

from .models import Submission, SubmissionState

logger = logging.getLogger(__name__)

# TODO: create a task for validate_submission and save log output
# somewhere

@shared_task
def process_submission(submission_id):
    """
    Handles the uploading of a submission.
    """
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)

    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    logger.info("Processing submission %s", submission_id)

    if state.status != 'pending-upload':
        logger.warning("Trying to process submission %s, but state is %s", submission, state.status)
        return

    try:
        reader = MFileReader()
        doc_ids = set(r.doc_id for r in db.select("SELECT doc_id FROM document_tag WHERE tag = %(tag)s", tag=submission.corpus_tag))
        with gzip.open(submission.uploaded_filename, 'rt') as f:
            mfile = reader.parse(f, doc_ids=doc_ids, logger=logger)
        api.upload_submission(submission_id, mfile)

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
def sample_submission(submission_id, type_='entity_relation', n_samples = 500):
    #TODO: Get the correct number of samples inside this function
    """
    Takes care of sampling from a submission to create evaluation_question and evaluation_batch.
    """
    assert Submission.objects.filter(id=submission_id).count() > 0,\
            "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0,\
            "SubmissionState {} does not exist!".format(submission_id)
    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    logger.info("Sampling submission %s", submission_id)
    if state.status != 'pending-sampling':
        logger.warning("Trying to process submission %s, but state is %s", submission, state.status)
        return

    try:
        sample_batch_id = _sample_submission(submission.corpus_tag, submission_id, type_, n_samples)
        assert len(api.get_samples(sample_batch_id)) > 0, "Sample did not generate any samples!"

        #Update the status of submission
        state.status = 'pending-turking'
        state.save()
        turk_submission.delay(sample_batch_id)
    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()

@shared_task
def turk_submission(sample_batch_id):
    """
    Takes care of turking from a submission from _sample.
    """
    submission_id = list(db.select("""
        SELECT submission_id FROM sample_batch WHERE id = %(batch_id)s
        """, batch_id = sample_batch_id))
    assert len(submission_id) == 1, "Sample batch {} does not exist!".format(sample_batch_id)

    submission_id = submission_id[0].submission_id
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)
    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    logger.info("Turking sample %s (submission %s)", sample_batch_id, submission_id)

    if state.status != 'pending-turking':
        logger.warning("Trying to process submission %s, but state is %s", submission, state.status)
        return
    try:
        evaluation_batch_id = create_evaluation_batch_from_submission_sample(sample_batch_id)
        assert evaluation_batch_id is not None, "Evaluation batch not created"
        evaluation_batch = api.get_question_batch(evaluation_batch_id)
        questions = api.get_questions(evaluation_batch_id)

        mturk_connection = connect(MTURK_TARGET)
        create_batch(mturk_connection, evaluation_batch.id, evaluation_batch.batch_type, questions)

        state.status = 'pending-annotation'
        state.save()

    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()
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
