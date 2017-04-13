#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to evaluate the system.
"""

import logging
from collections import Counter

from . import db

logger = logging.getLogger(__name__)

def get_submissions():
    return list(db.select("""SELECT * FROM submission"""))

def compute_exhaustive_distribution(corpus_tag):
    distribution = Counter()
    for row in db.select("""
        WITH _counts AS (
            SELECT COUNT(*) FROM evaluation_relation e, evaluation_batch b
            WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations' AND b.corpus_tag = %(tag)s)
        SELECT subject_id, relation, object_id, 1./c.count AS prob 
        FROM evaluation_relation e, evaluation_batch b, _counts c
        WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations'
          AND b.corpus_tag = %(tag)s
        """, tag=corpus_tag):
        distribution[row.subject_id, row.relation, row.object_id] = float(row.prob)
    return distribution

def test_compute_exhaustive_distribution():
    tag = 'kbp2016'
    distribution = compute_exhaustive_distribution(tag)
    value = sum(distribution.values())
    assert abs(value - 1.0) < 1.e-5, "Distribution is not normalized: Z = {}".format(value)

# Get distributions.
def compute_instance_distribution(corpus_tag, submission_id):
    distribution = Counter()
    for row in db.select("""
        WITH _counts AS (SELECT submission_id, COUNT(*) FROM submission_relation s GROUP BY submission_id)
        SELECT s.subject_id, s.relation, s.object_id, 1./c.count AS prob
        FROM submission_relation s, _counts c, submission s_
        WHERE s.submission_id = c.submission_id AND s.submission_id = s_.id
          AND s.submission_id = %(submission_id)s
          AND s_.corpus_tag = %(tag)s
        """, tag=corpus_tag, submission_id=submission_id):
        distribution[row.subject_id, row.relation, row.object_id] = float(row.prob)
    return distribution

def test_compute_instance_distribution():
    tag = 'kbp2016'
    for submission in get_submissions():
        P = compute_instance_distribution(tag, submission.id)
        Z = sum(P.values())
        assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def compute_relation_distribution(corpus_tag, submission_id):
    distribution = Counter()
    for row in db.select("""
        WITH _relations AS (SELECT submission_id, COUNT(DISTINCT relation) FROM submission_relation s GROUP BY submission_id),
             _counts AS (SELECT submission_id, relation, COUNT(*) FROM submission_relation s GROUP BY submission_id, relation)
        SELECT s.subject_id, s.relation, s.object_id, (1./c.count)/(r.count) AS prob
        FROM submission_relation s, _counts c, _relations r, submission s_
        WHERE s.submission_id = r.submission_id AND s.submission_id = c.submission_id AND s.relation = c.relation
          AND s.submission_id = %(submission_id)s
          AND s_.corpus_tag = %(tag)s
        """, tag=corpus_tag, submission_id=submission_id):
        distribution[row.subject_id, row.relation, row.object_id] = float(row.prob)
    return distribution

def test_compute_relation_distribution():
    tag = 'kbp2016'
    for submission in get_submissions():
        P = compute_relation_distribution(tag, submission.id)
        Z = sum(P.values())
        assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def compute_entity_distribution(corpus_tag, submission_id):
    distribution = Counter()
    for row in db.select("""
        WITH _entities AS (
                SELECT s.submission_id, COUNT(DISTINCT link_name) 
                FROM submission_relation s, submission_link l 
                WHERE s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND  s.subject_id = l.mention_id
                GROUP BY s.submission_id),
             _counts AS (
                SELECT s.submission_id, link_name, COUNT(*) 
                FROM submission_relation s, submission_link l
                WHERE s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND  s.subject_id = l.mention_id
                GROUP BY s.submission_id, link_name)
        SELECT s.subject_id, s.relation, s.object_id, l.link_name, (1./c.count)/(e.count) AS prob
        FROM submission_relation s, submission_link l, _counts c, _entities e, submission s_
        WHERE s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND  s.subject_id = l.mention_id
          AND s.submission_id = e.submission_id AND s.submission_id = c.submission_id AND c.link_name = l.link_name
          AND s_.id = s.submission_id
          AND s.submission_id = %(submission_id)s
          AND s_.corpus_tag = %(tag)s
        """, tag=corpus_tag, submission_id=submission_id):
        distribution[row.subject_id, row.relation, row.object_id] = float(row.prob)
    return distribution

def test_compute_entity_distribution():
    tag = 'kbp2016'
    for submission in get_submissions():
        P = compute_entity_distribution(tag, submission.id)
        Z = sum(P.values())
        assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def get_exhaustive_samples(corpus_tag):
    rows = db.select("""
        SELECT e.doc_id, e.subject_id, e.object_id, e.relation, e.weight
        FROM evaluation_relation e,
             evaluation_batch b 
        WHERE e.question_batch_id = b.id
         AND b.batch_type = 'exhaustive_relations'
         AND b.corpus_tag = %(tag)s
         AND e.weight > 0.5 AND e.relation <> 'no_relation'
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
          AND r.submission_id = %(submission_id)s 
          """, tag=corpus_tag, scheme=scheme, submission_id=submission_id)
    # TODO: ^^ is a hack to get the right rows from the database. we
    # should probably do differently.
    return [((row.subject_id, row.predicted_relation, row.object_id), 1.0 if row.predicted_relation == row.gold_relation else 0.0) for row in rows]
