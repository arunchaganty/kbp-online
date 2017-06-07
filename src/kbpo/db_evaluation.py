#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to evaluate the system.
"""

import logging
from collections import Counter

from . import db

logger = logging.getLogger(__name__)

def get_exhaustive_samples(corpus_tag):
    """
    Use the document_sample table to get which documents have been exhaustively sampled.
    """
    rows = db.select("""
        SELECT e.doc_id, e.subject_id, e.object_id, e.relation, e.weight
        FROM evaluation_relation e,
        JOIN document_sample s ON (e.doc_id = s.doc_id)
        JOIN document_tag t ON (e.doc_id = t.doc_id AND t.tag = %(corpus_tag)s)
        WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
        """, tag=corpus_tag)
    return [((row.subject_id, row.relation, row.object_id), 1.0) for row in rows]

def get_submission_samples(corpus_tag, scheme, submission_id):
    rows = db.select("""
        SELECT r.doc_id, r.subject_id, r.object_id, r.relation AS predicted_relation, e.relation AS gold_relation, b.params
        FROM submission_relation r,
             submission s,
             evaluation_relation e,
             evaluation_batch b 
        WHERE e.question_batch_id = b.id
          AND r.doc_id = e.doc_id AND r.subject_id = e.subject_id AND r.object_id = e.object_id
          AND r.submission_id = s.id
          AND b.corpus_tag = %(tag)s
          AND b.batch_type = 'selective_relations'
          AND b.params ~ %(scheme)s
          AND b.params ~ %(submission_f)s
          AND r.submission_id = %(submission_id)s 
          """, tag=corpus_tag,
                     scheme='"method":"{}"'.format(scheme),
                     submission_id=submission_id,
                     submission_f='"submission_id":{}'.format(submission_id)
                    )
    # TODO: ^^ is a hack to get the right rows from the database. we
    # should probably do differently.
    return [((row.subject_id, row.predicted_relation, row.object_id), 1.0 if row.predicted_relation == row.gold_relation else 0.0) for row in rows]
