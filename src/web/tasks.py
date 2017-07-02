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
from kbpo.parser import MFileReader, TacKbReader
from kbpo.evaluation_api import get_updated_scores, update_score
from kbpo.sampling import sample_submission as _sample_submission
from kbpo.questions import create_evaluation_batch_for_submission_sample
from kbpo.turk import connect, create_batch, mturk_batch_payments
from kbpo.web_data import parse_response,\
        verify_evaluation_mention_response, verify_evaluation_relation_response,\
        merge_evaluation_tables, check_batch_complete, get_hit_id, check_hit_complete
from django.core.mail import send_mail

from .models import Submission, SubmissionState, SubmissionUser, User

logger = logging.getLogger(__name__)

@shared_task
def validate_submission(submission_id, file_format, chain=True):
    """
    Validates submission.
    """
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)

    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    # Get the right reader
    if file_format == "mfile":
        reader = MFileReader()
    elif file_format == "tackb2016":
        reader = TacKbReader()
    else:
        raise ValueError("Invalid file format: {}".format(file_format))

    logger.info("Validating submission %s", submission_id)

    if state.status != 'pending-validation':
        logger.warning("Trying to validate submission %s, but state is %s", submission.id, state.status)
        return

    try:
        doc_ids = {r.doc_id for r in db.select("SELECT doc_id FROM document_tag WHERE tag = %(tag)s", tag=submission.corpus_tag)}

        with gzip.open(submission.log_filename, "wt") as log_file:
            _logger = logging.Logger("validation")
            _logger.setLevel(logging.INFO)
            _logger.addHandler(logging.StreamHandler(log_file))

            with gzip.open(submission.original_filename, 'rt') as f:
                # Check that it has the right format, aka validate it.
                mfile = reader.parse(f, doc_ids=doc_ids, logger=_logger)
        # TODO: We never stop the submission even if there are errors (maybe this should be reconsidered?)
        assert len(mfile.types) > 0, "Uploaded submission file does not define any mentions"
        assert len(mfile.relations) > 0, "Uploaded submission file does not define any relations"

        # Save parsed file.
        with gzip.open(submission.uploaded_filename, 'wt') as f:
            mfile.write(f)

        # Update state of submission.
        state.status = 'pending-upload'
        state.save()
        if chain:
            process_submission.delay(submission_id)
    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()


@shared_task
def process_submission(submission_id, chain=True):
    """
    Handles the uploading of a submission.
    """
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)

    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    logger.info("Processing submission %s", submission_id)

    if state.status != 'pending-upload':
        logger.warning("Trying to process submission %s, but state is %s", submission.id, state.status)
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
        if chain:
            sample_submission.delay(submission_id)
    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()

@shared_task
def sample_submission(submission_id, type_='entity_relation', n_samples=1000, chain=True):
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
        logger.warning("Trying to sample submission %s, but state is %s", submission, state.status)
        return

    try:
        sample_batch_id = _sample_submission(submission.corpus_tag, submission_id, type_, n_samples)
        assert len(api.get_samples(sample_batch_id)) > 0, "Sample did not generate any samples!"

        #Update the status of submission
        state.status = 'pending-turking'
        state.save()

        if chain:
            turk_submission.delay(submission_id, sample_batch_id)
    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()

@shared_task
def turk_submission(submission_id, sample_batch_id=None, chain=True):
    """
    Takes care of turking from a submission from _sample.
    """
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)
    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)

    logger.info("Turking submission %s", submission.id)

    if state.status != 'pending-turking':
        logger.warning("Trying to turk submission %s, but state is %s", submission.id, state.status)
        return
    try:
        sample_batches = api.get_submission_sample_batches(submission_id)
        assert len(sample_batches) > 0, "No sample batches to turk for submission {}".format(submission_id)

        if sample_batch_id is not None:
            assert any(batch == sample_batch_id for batch in sample_batches),\
                    "Sample batch {} is not part of submission {}".format(sample_batch_id, submission_id)
        else:
            # Pick the most recent sample batch.
            sample_batch_id = sample_batches[0]

        evaluation_batch_id = create_evaluation_batch_for_submission_sample(submission_id, sample_batch_id)
        if evaluation_batch_id is None:
            logger.warning("Evaluation batch not created because all possible questions have been asked!")
        else:
            evaluation_batch = api.get_question_batch(evaluation_batch_id)
            questions = api.get_questions(evaluation_batch_id)

            mturk_connection = connect(MTURK_TARGET)
            create_batch(mturk_connection, evaluation_batch.id, evaluation_batch.batch_type, questions)

        # Move state forward.
        state.status = 'pending-annotation'
        state.save()
    except Exception as e:
        logger.exception(e)
        state.status = 'error'
        state.message = str(e)
        state.save()

@shared_task
def process_responses(chain=True):
    """
    Processes all pending-extraction mturk responses to fill in evaluation_*_response tables
    """
    for row in db.select("""SELECT id FROM mturk_assignment WHERE state = 'pending-extraction'"""):
        process_response(row.id)

@shared_task
def process_response(assignment_id, chain=True):
    """
    Processes an mturk response to fill in evaluation_*_response tables
    """
    logger.info("Running process_response")
    try:
        mturk_batch_id = db.get("SELECT batch_id FROM mturk_assignment WHERE id = %(assignment_id)s",
                                assignment_id=assignment_id).batch_id
        hit_id = get_hit_id(assignment_id)
        hit_complete = check_hit_complete(hit_id)
        if hit_complete:
            for assignment_id in db.select("SELECT id FROM mturk_assignment WHERE hit_id = %(hit_id)s", hit_id = hit_id):
                parse_response(assignment_id)
                db.execute("UPDATE mturk_assignment SET state = %(new_state)s WHERE id = %(assignment_id)s",
                           new_state = 'pending-validation', assignment_id = assignment_id)
            db.execute("UPDATE mturk_hit SET state = 'pending-aggregation' WHERE id = %(hit_id)s", hit_id = hit_id)

    except Exception as e:  # Uh oh, these are errors that we should look at.
        db.execute("UPDATE mturk_assignment SET state = %(new_state)s, message = %(message)s WHERE id = %(assignment_id)s",
                   new_state = 'error', message=str(e), assignment_id = assignment_id)



    # Can't catch exception because batches don't have states.
    batch_complete = check_batch_complete(mturk_batch_id)
    if batch_complete:
        if chain:
            process_mturk_batch.delay(mturk_batch_id)

@shared_task
def process_mturk_batch(mturk_batch_id, force = False, chain=True):
    """
    First verifies if the reponses for a hit are sane
    then aggregates them to fill evaluation_* tables
    """
    logger.info("Running process_mturk_batch")

    # Actually merge all our tables.
    merge_evaluation_tables(mode='mturk_batch', mturk_batch_id = mturk_batch_id)

    # verify_evaluation_relation_response depends on majority relation directly
    # and verify_evaluation_mention_response looks at deviation from median,
    # so it depends on majority counts. Hence it doesn't seem like we can actually benefit from
    # merging only validated responses. The point of validation is then simply to discourage
    # spammers in the long run and doesn't help much in the correctness of the current batch
    # The only other alternative is to create a new mturk batch to cover the rejected assignments
    # TODO: Create a new mturk batch to cover rejected assignments
    verify_evaluation_mention_response()
    verify_evaluation_relation_response()

    mturk_connection = connect(MTURK_TARGET)
    mturk_batch_payments(mturk_connection, mturk_batch_id)

    db.execute("UPDATE mturk_hit SET state = 'done' WHERE batch_id = %(mturk_batch_id)s", mturk_batch_id = mturk_batch_id)

    submission_id = db.get("""
     SELECT DISTINCT submission_id 
     FROM mturk_hit 
     LEFT JOIN evaluation_batch ON evaluation_batch.id = mturk_hit.question_batch_id 
     LEFT JOIN submission_sample ON submission_sample.batch_id = evaluation_batch.sample_batch_id
     WHERE mturk_hit.batch_id = %(mturk_batch_id)s;
     """, mturk_batch_id = mturk_batch_id).submission_id
    assert Submission.objects.filter(id=submission_id).count() > 0, "Submission {} does not exist!".format(submission_id)
    assert SubmissionState.objects.filter(submission_id=submission_id).count() > 0, "SubmissionState {} does not exist!".format(submission_id)

    submission = Submission.objects.get(id=submission_id)
    state = SubmissionState.objects.get(submission_id=submission_id)
    state.status = 'pending-scoring'
    state.save()

    if chain:
        score_submission.delay(submission_id)

@shared_task
def score_submission(submission_id, chain=True):
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
        submissionuser = SubmissionUser.objects.get(submission=submission)
        user = User.objects.get(submissionuser=submissionuser)
        user.email_user(
            subject='KBP Online submission scored',
            message="""Your submission %(submission_name)s to KBP Online has been scored. 
            You can view it at kbpo.stanford.edu/submissions/
            
            Keep populating, 
            KBPO team
            """%{'submission_name':submission.name},
            from_email='kbp-online-owners@lists.stanford.edu',
        )


    except Exception as e:
        print(e)
        state.status = "error"
        state.message = e
        state.save()
