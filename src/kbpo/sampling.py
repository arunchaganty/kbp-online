"""
Generate samples for a corpus tag and for a submission.
"""

import json
import logging

import numpy as np

from . import db
from . import distribution
from .sample_util import sample_without_replacement
from .counter_utils import normalize

logger = logging.getLogger(__name__)

def sample_document_uniform(corpus_tag, n_samples):
    # Get distribution
    P = distribution.document_uniform(corpus_tag)

    # Get samples
    doc_ids = sample_without_replacement(P, n_samples)

    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""
                INSERT INTO sample_batch(distribution_type, corpus_tag, params) VALUES %s RETURNING id
                """, [('uniform', corpus_tag, json.dumps({'type':'uniform', 'with_replacement': False}),)])
            batch_id, = next(cur)
            db.execute_values(cur, """
                INSERT INTO document_sample(batch_id, doc_id) VALUES %s
                """, [(batch_id, doc_id) for doc_id in doc_ids])

def test_sample_document_uniform():
    np.random.seed(42)
    tag = 'kbp2016'

    db.execute("""TRUNCATE sample_batch CASCADE;
                   ALTER SEQUENCE sample_batch_id_seq RESTART;
                   """)
    sample_document_uniform(tag, 20)
    batches = list(db.select("""SELECT id, submission_id, distribution_type, corpus_tag, params FROM sample_batch"""))
    assert len(batches) == 1
    batch = batches[0]
    assert batch.id == 1
    assert batch.submission_id is None
    assert batch.distribution_type == "uniform"
    assert batch.corpus_tag == "kbp2016"
    assert batch.params == {"type":"uniform", "with_replacement": False}

    docs = list(db.select("""SELECT doc_id FROM document_sample WHERE batch_id=%(batch_id)s""", batch_id=batch.id))
    assert len(docs) == 20

def sample_document_entity(corpus_tag, n_samples, mention_table='evaluation_mention'):
    # Get documents
    seed_documents = [(row.doc_id,) for row in db.select("""
        SELECT s.doc_id
        FROM document_sample s,
             document_tag d
        WHERE s.doc_id = d.doc_id AND d.tag = %(corpus_tag)s
        """, corpus_tag=corpus_tag)]

    # Get distribution
    P = distribution.document_entity(corpus_tag, seed_documents, mention_table=mention_table)
    # Remove seed documents.
    for doc_id in seed_documents:
        P[doc_id] = 0.
    P = normalize(P)

    # Get samples
    doc_ids = sample_without_replacement(P, n_samples)

    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""
                INSERT INTO sample_batch(distribution_type, corpus_tag, params) VALUES %s RETURNING id
                """, [('entity', corpus_tag, json.dumps({'type':'entity', 'with_replacement': False}),)])
            batch_id, = next(cur)
            db.execute_values(cur, """
                INSERT INTO document_sample(batch_id, doc_id) VALUES %s
                """, [(batch_id, doc_id) for doc_id in doc_ids])

def test_sample_document_entity():
    tag = 'kbp2016'

    db.execute("""TRUNCATE sample_batch CASCADE;
                   ALTER SEQUENCE sample_batch_id_seq RESTART;
                   """)
    sample_document_uniform(tag, 20)
    sample_document_entity(tag, 20, mention_table="suggested_mention")

    batches = list(db.select("""SELECT id, submission_id, distribution_type, corpus_tag, params FROM sample_batch"""))
    assert len(batches) == 2
    batch = batches[1]
    assert batch.id == 2
    assert batch.submission_id is None
    assert batch.distribution_type == "entity"
    assert batch.corpus_tag == "kbp2016"
    assert batch.params == {"type":"entity", "with_replacement": False}

    docs = list(db.select("""SELECT doc_id FROM document_sample WHERE batch_id=%(batch_id)s""", batch_id=batch.id))
    assert len(docs) == 20

def sample_submission(corpus_tag, submission_id, type_, n_samples):
    # Get distribution
    if type_ == "instance":
        P = distribution.submission_instance(corpus_tag, submission_id)
    elif type_ == "relation":
        P = distribution.submission_relation(corpus_tag, submission_id)
    elif type_ == "entity":
        P = distribution.submission_entity(corpus_tag, submission_id)
    else:
        raise ValueError("Invalid submission sampling distribution type: {}".format(type_))

    # Get samples
    relation_mentions = sample_without_replacement(P[submission_id], n_samples)

    with db.CONN:
        with db.CONN.cursor() as cur:
            cur.execute("""
                INSERT INTO sample_batch(submission_id, distribution_type, corpus_tag, params) VALUES %s RETURNING id
                """, [(submission_id, type_, corpus_tag, json.dumps({'submission_id':submission_id, 'type':type_, 'with_replacement': False}),)])
            batch_id, = next(cur)
            db.execute_values(cur, """
                INSERT INTO submission_sample(batch_id, submission_id, doc_id, subject, object) VALUES %s
                """, [(batch_id, submission_id, doc_id, db.Int4NumericRange(*subject), db.Int4NumericRange(*object_)) for doc_id, subject, object_ in relation_mentions])

def test_sample_submission_instance():
    tag = 'kbp2016'
    submission_id = 1 # patterns

    db.execute("""TRUNCATE sample_batch CASCADE;
                   ALTER SEQUENCE sample_batch_id_seq RESTART;
                   """)
    sample_submission(tag, submission_id, 'instance', 20)

    batches = list(db.select("""SELECT id, submission_id, distribution_type, corpus_tag, params FROM sample_batch"""))
    assert len(batches) == 1
    batch = batches[0]
    assert batch.id == 1
    assert batch.submission_id == submission_id
    assert batch.distribution_type == "instance"
    assert batch.corpus_tag == "kbp2016"
    assert batch.params == {"submission_id": submission_id, "type":"instance", "with_replacement": False}

    relation_mentions = list(db.select("""SELECT doc_id, subject, object FROM submission_sample WHERE batch_id=%(batch_id)s AND submission_id=%(submission_id)s""", batch_id=batch.id, submission_id=submission_id))
    assert len(relation_mentions) == 20

def test_sample_submission_relation():
    tag = 'kbp2016'
    submission_id = 1 # patterns

    db.execute("""TRUNCATE sample_batch CASCADE;
                   ALTER SEQUENCE sample_batch_id_seq RESTART;
                   """)
    sample_submission(tag, submission_id, 'relation', 20)

    batches = list(db.select("""SELECT id, submission_id, distribution_type, corpus_tag, params FROM sample_batch"""))
    assert len(batches) == 1
    batch = batches[0]
    assert batch.id == 1
    assert batch.submission_id == submission_id
    assert batch.distribution_type == "relation"
    assert batch.corpus_tag == "kbp2016"
    assert batch.params == {"submission_id": submission_id, "type":"relation", "with_replacement": False}

    relation_mentions = list(db.select("""SELECT doc_id, subject, object FROM submission_sample WHERE batch_id=%(batch_id)s AND submission_id=%(submission_id)s""", batch_id=batch.id, submission_id=submission_id))
    assert len(relation_mentions) == 20

def test_sample_submission_entity():
    tag = 'kbp2016'
    submission_id = 1 # patterns

    db.execute("""TRUNCATE sample_batch CASCADE;
                   ALTER SEQUENCE sample_batch_id_seq RESTART;
                   """)
    sample_submission(tag, submission_id, 'entity', 20)

    batches = list(db.select("""SELECT id, submission_id, distribution_type, corpus_tag, params FROM sample_batch"""))
    assert len(batches) == 1
    batch = batches[0]
    assert batch.id == 1
    assert batch.submission_id == submission_id
    assert batch.distribution_type == "entity"
    assert batch.corpus_tag == "kbp2016"
    assert batch.params == {"submission_id": submission_id, "type":"entity", "with_replacement": False}

    relation_mentions = list(db.select("""SELECT doc_id, subject, object FROM submission_sample WHERE batch_id=%(batch_id)s AND submission_id=%(submission_id)s""", batch_id=batch.id, submission_id=submission_id))
    assert len(relation_mentions) == 20
