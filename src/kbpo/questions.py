"""
Routines to create questions.
"""
import pdb
import json
import logging
from hashlib import sha1
from tqdm import tqdm

from . import db
from . import api
from . import turk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# TODO: allow us to 'override' and add samples to questions that have already been answered.
def create_questions_for_submission_sample(submission_id, sample_batch_id):
    """
    Produces questions for a submission, based on what's in the
    database.
    """
    questions = []
    for row in db.select("""
    WITH _sampled_relations AS (
        (SELECT DISTINCT doc_id, LEAST(subject, object) AS subject, GREATEST(subject, object) AS object
        FROM submission_sample s
        WHERE s.submission_id = %(submission_id)s
          AND s.batch_id = %(sample_batch_id)s)
        EXCEPT (
            (SELECT doc_id, subject, object
                FROM evaluation_question q
                JOIN evaluation_relation_question r ON (q.id = r.id AND q.batch_id = r.batch_id)
                WHERE (q.state <> 'error' OR q.state <> 'revoked'))
            UNION 
            (SELECT doc_id, object, subject
                FROM evaluation_question q
                JOIN evaluation_relation_question r ON (q.id = r.id AND q.batch_id = r.batch_id)
                WHERE (q.state <> 'error' OR q.state <> 'revoked'))
            UNION
            (SELECT doc_id, subject, object FROM evaluation_relation q)
            UNION
            (SELECT doc_id, object, subject FROM evaluation_relation q)
        ))
        SELECT s.doc_id, s.subject, s.object, r.subject_type, r.object_type
        FROM _sampled_relations s
        JOIN submission_entity_relation r ON (
            r.submission_id = %(submission_id)s
            AND s.doc_id = r.doc_id AND s.subject = r.subject AND s.object = r.object);
        ;
        """, submission_id=submission_id, sample_batch_id=sample_batch_id):
        # In some cases, we will need to flip types.
        if row.subject_type == 'ORG' and row.object_type == 'PER':
            subject, object_ = row.object, row.subject
        elif row.subject_type == 'GPE':
            subject, object_ = row.object, row.subject
        else:
            subject, object_ = row.subject, row.object

        questions.append({
            "batch_type": "selective_relations",
            "submission_id": submission_id,
            "doc_id": row.doc_id,
            "subject": (subject.lower, subject.upper),
            "object": (object_.lower, object_.upper),
            })
    return questions

def create_questions_for_corpus(corpus_tag):
    """
    Produces questions for a submission, based on what's in the
    database.
    """
    questions = []
    for row in db.select("""
        (SELECT DISTINCT doc_id
        FROM document_sample s
        JOIN document_tag t ON (s.doc_id = t.doc_id)
        WHERE  t.tag=%(corpus_tag)s)
        EXCEPT 
        (SELECT doc_id
        FROM evaluation_question q
        JOIN evaluation_doc_question d ON (q.id = d.id AND q.batch_id = d.batch_id)
        WHERE q.state <> 'error');
        """, corpus_tag=corpus_tag):
        questions.append({
            "batch_type": "exhaustive_mentions",
            "doc_id": row.doc_id,
            })
    return questions

def validate_question_params(params):
    assert "batch_type" in params
    if params["batch_type"] == "exhaustive_mentions":
        assert "doc_id" in params
    elif params["batch_type"] == "exhaustive_relations":
        assert "doc_id" in params
        assert "subject" in params
        assert "object" in params
    elif params["batch_type"] == "selective_relations":
        assert "doc_id" in params
        assert "subject" in params
        assert "object" in params
    else:
        assert False, "Invalid batch type: {}".format(params["batch_type"])

def insert_evaluation_question(batch_id, params, cur=None):
    validate_question_params(params)

    if cur is None:
        with db.CONN:
            with db.CONN.cursor() as cur:
                return insert_evaluation_question(batch_id, params, cur)
    else:
        params_str = json.dumps(params)
        id_ = sha1(params_str.encode("utf-8")).hexdigest()
        cur.execute(
            """INSERT INTO evaluation_question(id, batch_id, state, params) VALUES %s""",
            [(id_, batch_id, "pending-turking", params_str)]
            )

def test_insert_evaluation_question():
    # TODO: Create a test database for this.
    raise NotImplementedError()

def insert_evaluation_batch(corpus_tag, batch_type, description, questions, cur=None):
    """
    Creates an evaluation batch with a set of questions.
    @questions is a list of parameters to launch tasks with.
    """
    for params in questions: validate_question_params(params)

    if cur is None:
        with db.CONN:
            with db.CONN.cursor() as cur:
                return insert_evaluation_batch(corpus_tag, batch_type, description, questions, cur)
    else:
        # Create new batch.
        cur.execute("""
            INSERT INTO evaluation_batch(corpus_tag, batch_type, description) VALUES %s
            RETURNING (id);
            """, [(corpus_tag, batch_type, description)])
        batch_id, = next(cur)
        questions = [json.dumps(params, sort_keys=True) for params in questions]
        ids = [sha1(params.encode("utf-8")).hexdigest() for params in questions]

        db.execute_values(
            cur,
            """INSERT INTO evaluation_question(id, batch_id, state, params) VALUES %s""",
            [(id_, batch_id, "pending-turking", params) for id_, params in zip(ids, questions)])

        return batch_id

def test_insert_evaluation_batch():
    # TODO: Create a test database for this.
    raise NotImplementedError()

def create_evaluation_batch_for_submission_sample(submission_id, sample_batch_id):
    submission = api.get_submission(submission_id)

    # First of all, make sure there are even samples for this submission.
    batches = api.get_submission_sample_batches(submission_id)
    assert len(batches) > 0,\
            "No sample batches for submission {}".format(submission_id)
    assert any(batch.id == sample_batch_id for batch in batches),\
            "Sample batch {} is not part of submission {}".format(sample_batch_id, submission_id)

    # Now, get the questions.
    questions = create_questions_for_submission_sample(submission_id, sample_batch_id)
    if len(questions) == 0:
        logger.warning("There are unasked questions for submission %s!", submission_id)
        return None

    # Create an evaluation_batch out of these questions.
    batch_type = 'selective_relations'
    description = "{} unique questions asked from submission {} ({})".format(len(questions), submission.name, submission_id)
    evaluation_batch_id = insert_evaluation_batch(submission.corpus_tag, batch_type, description, questions)
    return evaluation_batch_id

def revoke_question(question_batch_id, question_id, mturk_conn=None):
    if mturk_conn is None:
        mturk_conn = turk.connect()

    # Revoke all mturk hits associated with this question.
    hits = db.select("""
        SELECT id
        FROM mturk_hit
        WHERE question_batch_id = %(question_batch_id)s AND question_id = %(question_id)s
        AND state <> 'revoked'
        """, question_batch_id=question_batch_id, question_id=question_id)

    had_errors = False
    for row in hits:
        try:
            turk.revoke_hit(mturk_conn, row.id)

            db.execute("""
                UPDATE mturk_hit
                SET state = %(state)s, message = %(message)s
                WHERE id=%(hit_id)s
                """, state="revoked", message="",
                       hit_id=row.id)
        except turk.HitMustBeReviewed as e:
            logger.exception(e)
            had_errors = True
            continue
    if not had_errors:
        db.execute("""
            UPDATE evaluation_question
            SET state=%(state)s, message=%(message)s
            WHERE id=%(question_id)s AND batch_id=%(question_batch_id)s
            """, state="revoked", message="",
                   question_batch_id=question_batch_id, question_id=question_id)

def revoke_question_batch(question_batch_id, mturk_conn=None):
    questions = api.get_questions(question_batch_id)
    if mturk_conn is None:
        mturk_conn = turk.connect()

    # Revoke all mturk hits associated with this question.
    for question in tqdm(questions, desc="revoking question batch"):
        revoke_question(question_batch_id, question.id, mturk_conn=mturk_conn)
