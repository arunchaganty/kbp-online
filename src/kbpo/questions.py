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

def create_questions_for_submission(submission_id):
    """
    Produces questions for a submission, based on what's in the
    database.
    """
    questions = []
    for row in db.select("""
        (SELECT DISTINCT doc_id, subject, object
        FROM submission_sample s
        WHERE s.submission_id = %(submission_id)s)
        EXCEPT 
        (SELECT doc_id, subject, object
        FROM evaluation_question q
        JOIN evaluation_relation_question r ON (q.id = r.question_id AND q.batch_id = r.batch_id)
        WHERE q.state <> 'error');
        """, submission_id=submission_id):
        questions.append({
            "batch_type": "selective_relations",
            "submission_id": submission_id,
            "doc_id": row.doc_id,
            "subject": (row.subject.lower, row.subject.upper),
            "object": (row.object.lower, row.object.upper),
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
        JOIN evaluation_doc_question d ON (q.id = d.question_id AND q.batch_id = d.batch_id)
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

def get_evaluation_batch(batch_id):
    return next(db.select("""
        SELECT id, corpus_tag, batch_type, description
        FROM evaluation_batch
        WHERE id=%(batch_id)s
        """, batch_id=batch_id))

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
            [(id_, batch_id, "pending-turking-0", params_str)]
            )

        # Insert into evaluation_?_question
        if params["batch_type"] == "exhaustive_mentions":
            cur.execute(
                """INSERT INTO evaluation_doc_question(question_id, batch_id, doc_id) VALUES %s""",
                [(id_, batch_id, params["doc_id"])]
                )
        elif params["batch_type"] == "exhaustive_relations" or params["batch_type"] == "selective_relations":
            cur.execute(
                """INSERT INTO evaluation_relation_question(question_id, batch_id, doc_id, subject, object) VALUES %s""",
                [(id_, batch_id, params["doc_id"], db.Int4NumericRange(*params["subject"]), db.Int4NumericRange(*params["object"]))]
                )
        else:
            raise ValueError("Invalid batch type: {}".format(params["batch_type"]))

def test_insert_evaluation_question():
    # TODO: Create a test database for this.
    raise NotImplementedError()

def insert_evaluation_batch(corpus_tag, batch_type, description, questions, cur=None):
    """
    Creates an evaluation batch with a set of questions.
    @questions is a list of parameters to launch tasks with.
    """
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
        ids = [sha1(json.dumps(params).encode("utf-8")).hexdigest() for params in questions]

        db.execute_values(
            cur,
            """INSERT INTO evaluation_question(id, batch_id, state, params) VALUES %s""",
            [(id_, batch_id, "pending-turking-0", json.dumps(params)) for id_, params in zip(ids, questions)])

        # Insert into evaluation_?_question
        if batch_type == "exhaustive_mentions":
            db.execute_values(
                cur,
                """INSERT INTO evaluation_doc_question(question_id, batch_id, doc_id) VALUES %s""",
                [(id_, batch_id, params["doc_id"]) for id_, params in zip(ids, questions)]
                )
        elif batch_type == "exhaustive_relations" or batch_type == "selective_relations":
            db.execute_values(
                cur,
                """INSERT INTO evaluation_relation_question(question_id, batch_id, doc_id, subject, object) VALUES %s""",
                [(id_, batch_id, params["doc_id"], db.Int4NumericRange(*params["subject"]), db.Int4NumericRange(*params["object"])) for id_, params in zip(ids, questions)]
                )
        else:
            raise ValueError("Invalid batch type: {}".format(batch_type))

        return batch_id

def test_insert_evaluation_batch():
    # TODO: Create a test database for this.
    raise NotImplementedError()

# TODO: Refactor to use some of the above.
def create_evaluation_batch_from_submission_sample(batch_id):
    #Contains all questions asked
    corpus_tag, name, details, distribution = next(db.select(
        """
        SELECT DISTINCT s.corpus_tag, name, details, distribution_type
        FROM submission AS s
        JOIN sample_batch AS sb ON (s.id = sb.submission_id AND sb.id = %(batch_id)s)
        LIMIT 1;
        """, batch_id = batch_id))
    existing_questions = list(db.select("""
        SELECT params->>'doc_id' AS doc_id,
              params->'mention_1' AS m1,
              params->'mention_2' AS m2
        FROM evaluation_question
        WHERE params->>'batch_type' = 'selective_relations'
        """))

    # Just for surety (as the response data could have been loaded from
    # a separate source, i.e. without having been created as an
    # evaluation question)
    existing_responses = list(db.select("""
        SELECT doc_id, subject AS m1, object AS m2 from evaluation_relation;
        """))
    existing = set(
        [(m.doc_id, tuple(m.m1[1:]), tuple(m.m2[1:])) for m in existing_questions] +
        [(m.doc_id, (m.m1.lower, m.m1.upper), (m.m2.lower, m.m2.upper)) for m in existing_responses] +
        [(m.doc_id, tuple(m.m2[1:]), tuple(m.m1[1:])) for m in existing_questions] +
        [(m.doc_id, (m.m2.lower, m.m2.upper), (m.m1.lower, m.m1.upper)) for m in existing_responses]
        )

    new_questions = db.select("""
        SELECT doc_id, subject AS m1, object AS m2 from submission_sample WHERE batch_id = %(batch_id)s;
        """, batch_id = batch_id)
    proposed = set([(m.doc_id, (m.m1.lower, m.m1.upper), (m.m2.lower, m.m2.upper)) for m in new_questions])
    new_questions = proposed - existing

    if len(list(new_questions)) > 0:
        with db.CONN:
            with db.CONN.cursor() as cur:
                description = "%d unique instances sampled from submission %s (%s) using distribution %s" % (len(list(new_questions)), name, details, distribution)
                evaluation_batch_id = next(db.select("""
                    INSERT INTO evaluation_batch (batch_type, corpus_tag, description, sample_batch_id) 
                    VALUES (%(batch_type)s, %(corpus_tag)s, %(description)s, $(sample_batch_id)s) RETURNING id
                    """, cur = cur, batch_type = 'selective_relations', corpus_tag = corpus_tag, description = description, sample_batch_id = batch_id))
                values = []
                for q in tqdm(list(new_questions)):
                    doc_id, m1, m2 = q
                    params = {'batch_type': 'selective_relations', 'mention_1': [doc_id, m1[0], m1[1]], 'mention_2': [doc_id, m2[0], m2[1]], 'doc_id': doc_id}
                    params_json = json.dumps(params, sort_keys = True)
                    row_id = sha1(params_json.encode('utf-8')).hexdigest
                    values.append((evaluation_batch_id.id, row_id, params_json, 'pending-turking'))

                db.execute_values(cur, "INSERT INTO evaluation_question(batch_id, id, params, state) VALUES %s",
                                  values)
    else:
        logger.warning("All the samples have already been asked as questions")
    return evaluation_batch_id

def revoke_question(question_batch_id, question_id, mturk_conn=None):
    if mturk_conn is None:
        mturk_conn = turk.connect()

    # Revoke all mturk hits associated with this question.
    with db.CONN:
        with db.CONN.cursor() as cur:
            for row in db.select("""
                SELECT id
                FROM mturk_hit
                WHERE question_batch_id = %(question_batch_id)s AND question_id = %(question_id)s
                """, cur=cur, question_batch_id=question_batch_id, question_id=question_id):
                turk.revoke_hit(mturk_conn, row.id)
            db.execute("""
                UPDATE evaluation_question
                SET state=%(state)s, message=%(message)s
                WHERE id=%(question_id)s AND batch_id=%(question_batch_id)s
                """, cur=cur, state="revoked", message="",
                       question_batch_id=question_batch_id, question_id=question_id)

def revoke_question_batch(question_batch_id, mturk_conn=None):
    questions = api.get_questions(question_batch_id)
    if mturk_conn is None:
        mturk_conn = turk.connect()

    # Revoke all mturk hits associated with this question.
    for question in questions:
        revoke_question(question_batch_id, question.id, mturk_conn=mturk_conn)
