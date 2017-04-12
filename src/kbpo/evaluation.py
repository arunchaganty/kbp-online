#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routines to evaluate the system.
"""

import pdb
import math
import logging

from collections import Counter

from . import db

logger = logging.getLogger(__name__)

def compute_exhaustive_distribution(corpus_tag):
    distribution = Counter()
    for row in db.select("""
WITH _counts AS (
    SELECT COUNT(*) FROM evaluation_relation e, evaluation_batch b
    WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations' AND b.corpus_tag = %(tag)s)
SELECT doc_id, subject_id, object_id, 1./c.count AS prob 
FROM evaluation_relation e, evaluation_batch b, _counts c
WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations'
  AND b.corpus_tag = %(tag)s
""", tag=corpus_tag):
        distribution[row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_exhaustive_distribution():
    tag = 'kbp2016'
    distribution = compute_exhaustive_distribution(tag)
    value = sum(distribution.values())
    assert abs(value - 1.0) < 1.e-5, "Distribution is not normalized: Z = {}".format(value)

def compute_instance_distribution(corpus_tag):
    distribution = Counter()
    for row in db.select("""
WITH _counts AS (SELECT submission_id, COUNT(*) FROM submission_relation s GROUP BY submission_id)
SELECT s.submission_id, s.doc_id, s.subject_id, s.object_id, 1./c.count AS prob
FROM submission_relation s, _counts c, submission s_
WHERE s.submission_id = c.submission_id AND s.submission_id = s_.id
  AND s_.corpus_tag = %(tag)s
""", tag=corpus_tag):
        distribution[row.submission_id, row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_instance_distribution():
    tag = 'kbp2016'
    distribution = compute_instance_distribution(tag)
    submission_counts = Counter()
    for row, value in distribution.items():
        submission_counts[row[0]] += value
    for submission_id, value in submission_counts.items():
        assert abs(value - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission_id, value)

def compute_relation_distribution(corpus_tag):
    distribution = Counter()
    for row in db.select("""
WITH _relations AS (SELECT submission_id, COUNT(DISTINCT relation) FROM submission_relation s GROUP BY submission_id),
     _counts AS (SELECT submission_id, relation, COUNT(*) FROM submission_relation s GROUP BY submission_id, relation)
SELECT s.submission_id, s.doc_id, s.subject_id, s.object_id, (1./c.count)/(r.count) AS prob
FROM submission_relation s, _counts c, _relations r, submission s_
WHERE s.submission_id = r.submission_id AND s.submission_id = c.submission_id AND s.relation = c.relation
  AND s.submission_id = s_.id AND s_.corpus_tag = %(tag)s
""", tag=corpus_tag):
        distribution[row.submission_id, row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_relation_distribution():
    tag = 'kbp2016'
    distribution = compute_relation_distribution(tag)
    submission_counts = Counter()
    for row, value in distribution.items():
        submission_counts[row[0]] += value
    for submission_id, value in submission_counts.items():
        assert abs(value - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission_id, value)

def compute_entity_distribution(corpus_tag):
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
SELECT s.submission_id, s.doc_id, s.subject_id, s.object_id, l.link_name, (1./c.count)/(e.count) AS prob
FROM submission_relation s, submission_link l, _counts c, _entities e, submission s_
WHERE s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND  s.subject_id = l.mention_id
  AND s.submission_id = e.submission_id AND s.submission_id = c.submission_id AND c.link_name = l.link_name
  AND s_.id = s.submission_id AND s_.corpus_tag = %(tag)s
""", tag=corpus_tag):
        distribution[row.submission_id, row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_entity_distribution():
    tag = 'kbp2016'
    distribution = compute_entity_distribution(tag)
    submission_counts = Counter()
    for row, value in distribution.items():
        submission_counts[row[0]] += value
    for submission_id, value in submission_counts.items():
        assert abs(value - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission_id, value)

def precision(submission_id, P, Q):
    """
    Evaluates the output from submission @submission_id.
    """
    # Grab all the data evaluated that intersects with the system output
    # and information regarding where it was sampled from.
    correct, predicted = 0., 0.
    for row in db.select("""
SELECT r.doc_id, r.subject_id, r.object_id, r.relation AS predicted_relation, e.relation AS gold_relation
FROM submission_relation r,
     submission s,
     evaluation_relation e
WHERE r.doc_id = e.doc_id AND r.subject_id = e.subject_id AND r.object_id = e.object_id
  AND r.submission_id = %(submission_id)s AND r.submission_id = s.id
  """, submission_id=submission_id):

        key = row.doc_id, row.subject_id, row.object_id
        if row.predicted_relation == row.gold_relation:
            correct += P[(submission_id,) + key]/Q[key]
        predicted += P[(submission_id,) + key]/Q[key] # self-normalizes the result
    return correct/predicted

def entity_precision(submission_id, P, Q):
    """
    Evaluates the output from submission @submission_id.
    """
    # Grab all the data evaluated that intersects with the system output
    # and information regarding where it was sampled from.
    correct, predicted = 0., 0.
    for row in db.select("""
SELECT r.doc_id, r.subject_id, r.object_id, r.relation AS predicted_relation, e.relation AS gold_relation
FROM submission_relation r,
     submission s,
     evaluation_relation e,
     evaluation_link el,
     evaluation_mention em
WHERE r.doc_id = e.doc_id AND r.subject_id = e.subject_id AND r.object_id = e.object_id
  AND r.submission_id = %(submission_id)s AND r.submission_id = s.id
  AND e.subject_id = el.mention_id AND e.subject_id = em.mention_id
  AND el.weight > 0.5 AND em.weight > 0.5
  """, submission_id=submission_id):

        key = row.doc_id, row.subject_id, row.object_id
        if row.predicted_relation == row.gold_relation:
            correct += P[(submission_id,) + key]/Q[key]
        predicted += P[(submission_id,) + key]/Q[key] # self-normalizes the result
    return correct/predicted


def exhaustive_recall(corpus_tag, submission_id):
    predicted_correct, total_correct = 0., 0.
    # Grab all the data evaluated that intersects with the system output
    # and information regarding where it was sampled from.

    for row in db.select("""
SELECT e.doc_id, e.subject_id, e.object_id, r.relation AS predicted_relation, e.relation AS gold_relation, e.weight, q.params
FROM evaluation_relation e
LEFT OUTER JOIN submission_relation r ON (r.doc_id = e.doc_id AND r.subject_id = e.subject_id AND r.object_id = e.object_id AND r.submission_id = %(submission_id)s)
JOIN evaluation_batch b ON (e.question_batch_id = b.id AND b.corpus_tag = %(tag)s)
JOIN evaluation_question q ON (e.question_id = q.id AND e.question_batch_id = q.batch_id)
WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
  AND b.batch_type = 'exhaustive_relations'
""", submission_id=submission_id, tag=corpus_tag):
        if row.predicted_relation == row.gold_relation:
            predicted_correct += 1.
        total_correct += 1.
    return predicted_correct/total_correct

def exhaustive_pooled_recall(corpus_tag):
    predicted_correct, total_correct = 0., 0.
    for row in db.select("""
SELECT DISTINCT e.doc_id, e.subject_id, e.object_id, s.relation AS predicted_relation, e.relation AS gold_relation
FROM evaluation_relation e
LEFT OUTER JOIN submission_relation s ON (s.doc_id = e.doc_id AND s.subject_id = e.subject_id AND s.object_id = e.object_id AND e.relation = s.relation)
JOIN evaluation_batch b ON (e.question_batch_id = b.id)
JOIN evaluation_question q ON (e.question_id = q.id AND e.question_batch_id = q.batch_id)
WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
  AND b.batch_type = 'exhaustive_relations'
  AND b.corpus_tag = %(tag)s
""", tag=corpus_tag):
        assert row.predicted_relation is None or row.predicted_relation == row.gold_relation
        if row.predicted_relation == row.gold_relation:
            predicted_correct += 1.
        total_correct += 1.
    return predicted_correct/total_correct

def pooled_recall(corpus_tag, submission_id, P, Q):
    """
    Evaluates the output from submission @submission_id.
    """

    predicted_correct, total_correct = 0., 0.
    # Grab all the data evaluated that intersects with the system output
    # and information regarding where it was sampled from.
    for row in db.select("""
SELECT e.doc_id, e.subject_id, e.object_id, r.relation AS predicted_relation, e.relation AS gold_relation
FROM evaluation_relation e
LEFT OUTER JOIN submission_relation r ON (r.doc_id = e.doc_id AND r.subject_id = e.subject_id AND r.object_id = e.object_id AND r.submission_id = %(submission_id)s)
JOIN evaluation_question q ON (e.question_id = q.id AND e.question_batch_id = q.batch_id)
JOIN evaluation_batch b ON (e.question_batch_id = b.id AND b.corpus_tag = %(tag)s AND b.batch_type = 'selective_relations')
WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
""", submission_id=submission_id, tag=corpus_tag):

        key = row.doc_id, row.subject_id, row.object_id
        if row.predicted_relation == row.gold_relation:
            predicted_correct += P[(submission_id,) + key]/Q[key]
        total_correct += 1
    return predicted_correct/total_correct

def score(submission_id, mode="instance"):
    corpus_tag, = next(db.select("""SELECT corpus_tag FROM submission WHERE id = %(submission_id)s""", submission_id=submission_id))

    Pi = compute_instance_distribution(corpus_tag)
    Pr = compute_relation_distribution(corpus_tag)
    Pe = compute_entity_distribution(corpus_tag)
    PE = compute_exhaustive_distribution(corpus_tag)

    # TODO: fix weights to be proportional to how often they appear 
    n_systems = 3
    z = 2*3 + 1
    Q = Counter()
    for k, v in PE.items(): Q[k] += v/z 
    #for k, v in Pi.items(): Q[k[1:]] += v/(4*3)
    for k, v in Pr.items(): Q[k[1:]] += v/z
    for k, v in Pe.items(): Q[k[1:]] += v/z
    print(sum(Q.values()))

    if mode == "instance":
        P = Pi
    elif mode == "relation":
        P = Pr
    elif mode == "entity":
        P = Pe
    else:
        raise ValueError("Invalid sampling mode {}".format(mode))

    p = precision(submission_id, P, Q)
    pe = entity_precision(submission_id, P, Q)
    logger.info("%.4f vs %.4f", p, pe)
    r_ = exhaustive_recall(corpus_tag, submission_id)
    re = exhaustive_pooled_recall(corpus_tag)
    rp = pooled_recall(corpus_tag, submission_id, P, Q)
    r = re * rp
    logger.info("Pool recall is %.4f and recall on pool is %.4f; total is %.4f vs %.4f", re, rp, r, r_)
    r = (r+r_)/2
    f1 = 2 * p * r / (p+r) if p+r > 0. else 0.
    return p, r, f1
