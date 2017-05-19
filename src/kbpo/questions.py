"""
Routines to create questions.
"""
import json
from hashlib import sha1

from . import db

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
