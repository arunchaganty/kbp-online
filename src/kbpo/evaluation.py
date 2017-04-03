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

def compute_exhaustive_distribution():
    distribution = Counter()
    for row in db.select("""
WITH _counts AS (
    SELECT COUNT(*) FROM evaluation_relation e, evaluation_batch b
    WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations')
SELECT doc_id, subject_id, object_id, 1./c.count AS prob 
FROM evaluation_relation e, evaluation_batch b, _counts c
    WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations'
"""):
        distribution[row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def compute_instance_distribution():
    distribution = Counter()
    for row in db.select("""
WITH _counts AS (SELECT submission_id, COUNT(*) FROM submission_relation s GROUP BY submission_id)
SELECT s.submission_id, s.doc_id, s.subject_id, s.object_id, 1./c.count AS prob
FROM submission_relation s, _counts c
WHERE s.submission_id = c.submission_id
"""):
        distribution[row.submission_id, row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_instance_distribution():
    distribution = compute_instance_distribution()
    submission_counts = Counter()
    for row, value in distribution.items():
        submission_counts[row[0]] += value
    for submission_id, value in submission_counts.items():
        assert abs(value - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission_id, value)

def compute_relation_distribution():
    distribution = Counter()
    for row in db.select("""
WITH _relations AS (SELECT submission_id, COUNT(DISTINCT relation) FROM submission_relation s GROUP BY submission_id),
     _counts AS (SELECT submission_id, relation, COUNT(*) FROM submission_relation s GROUP BY submission_id, relation)
SELECT s.submission_id, s.doc_id, s.subject_id, s.object_id, (1./c.count)/(r.count) AS prob
FROM submission_relation s, _counts c, _relations r
WHERE s.submission_id = c.submission_id AND r.submission_id = s.submission_id
  AND c.relation = s.relation
"""):
        distribution[row.submission_id, row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_relation_distribution():
    distribution = compute_relation_distribution()
    submission_counts = Counter()
    for row, value in distribution.items():
        submission_counts[row[0]] += value
    for submission_id, value in submission_counts.items():
        assert abs(value - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission_id, value)

def compute_entity_distribution():
    # TODO: handle linking.
    distribution = Counter()
    for row in db.select("""
WITH _entities AS (SELECT submission_id, COUNT(DISTINCT hashspan(subject_id)) FROM submission_relation s GROUP BY submission_id),
     _counts AS (SELECT submission_id, subject_id, COUNT(*) FROM submission_relation s GROUP BY submission_id, subject_id)
SELECT s.submission_id, s.doc_id, s.subject_id, s.object_id, (1./c.count)/(e.count) AS prob
FROM submission_relation s, _counts c, _entities e
WHERE s.submission_id = c.submission_id AND e.submission_id = s.submission_id
  AND c.subject_id = s.subject_id
"""):
        distribution[row.submission_id, row.doc_id, row.subject_id, row.object_id] = float(row.prob)
    return distribution

def test_compute_entity_distribution():
    distribution = compute_entity_distribution()
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
SELECT s.doc_id, s.subject_id, s.object_id, s.relation AS predicted_relation, e.relation AS gold_relation, weight
FROM submission_relation s,
     evaluation_relation e
WHERE s.doc_id = e.doc_id AND s.subject_id = e.subject_id AND s.object_id = e.object_id
  AND s.submission_id = %(submission_id)s
  """, submission_id=submission_id):

        key = row.doc_id, row.subject_id, row.object_id
        if row.predicted_relation == row.gold_relation:
            correct += P[(submission_id,) + key]/Q[key]
        predicted += 1
    return correct/predicted

def exhaustive_recall(submission_id):
    predicted_correct, total_correct = 0., 0.
    # Grab all the data evaluated that intersects with the system output
    # and information regarding where it was sampled from.

    # TODO: make sure document sets, etc. match.
    for row in db.select("""
SELECT e.doc_id, e.subject_id, e.object_id, s.relation AS predicted_relation, e.relation AS gold_relation, e.weight, q.params
FROM evaluation_relation e
JOIN evaluation_batch b ON (e.question_batch_id = b.id)
LEFT OUTER JOIN submission_relation s ON (s.doc_id = e.doc_id AND s.subject_id = e.subject_id AND s.object_id = e.object_id AND s.submission_id = %(submission_id)s)
JOIN evaluation_question q ON (e.question_id = q.id AND e.question_batch_id = q.batch_id)
WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
  AND b.batch_type = 'exhaustive_relations'
""", submission_id=submission_id):
        if row.predicted_relation == row.gold_relation:
            predicted_correct += 1.
        total_correct += 1.
    return predicted_correct/total_correct

def exhaustive_pooled_recall():
    predicted_correct, total_correct = 0., 0.
    for row in db.select("""
SELECT DISTINCT e.doc_id, e.subject_id, e.object_id, s.relation AS predicted_relation, e.relation AS gold_relation
FROM evaluation_relation e
LEFT OUTER JOIN submission_relation s ON (s.doc_id = e.doc_id AND s.subject_id = e.subject_id AND s.object_id = e.object_id AND e.relation = s.relation)
JOIN evaluation_batch b ON (e.question_batch_id = b.id)
JOIN evaluation_question q ON (e.question_id = q.id AND e.question_batch_id = q.batch_id)
WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
  AND b.batch_type = 'exhaustive_relations'
"""):
        assert row.predicted_relation is None or row.predicted_relation == row.gold_relation
        if row.predicted_relation == row.gold_relation:
            predicted_correct += 1.
        total_correct += 1.
    return predicted_correct/total_correct

def pooled_recall(submission_id, P, Q):
    """
    Evaluates the output from submission @submission_id.
    """

    # TODO: handle exhaustive/selective measurement properly.

    predicted_correct, total_correct = 0., 0.
    # Grab all the data evaluated that intersects with the system output
    # and information regarding where it was sampled from.
    for row in db.select("""
SELECT e.doc_id, e.subject_id, e.object_id, s.relation AS predicted_relation, e.relation AS gold_relation, e.weight, q.params
FROM evaluation_relation e
LEFT OUTER JOIN submission_relation s ON (s.doc_id = e.doc_id AND s.subject_id = e.subject_id AND s.object_id = e.object_id AND s.submission_id = %(submission_id)s)
JOIN evaluation_question q ON (e.question_id = q.id AND e.question_batch_id = q.batch_id)
WHERE e.weight > 0.5 AND e.relation <> 'no_relation'
""", submission_id=submission_id):

        key = row.doc_id, row.subject_id, row.object_id
        if row.predicted_relation == row.gold_relation:
            predicted_correct += P[(submission_id,) + key]/Q[key]
        total_correct += 1
    return predicted_correct/total_correct

def score(submission_id, mode="instance"):
    PE = compute_exhaustive_distribution()
    Pi = compute_instance_distribution()
    Pr = compute_relation_distribution()
    Pe = compute_entity_distribution()

    Q = Counter()
    for k, v in PE.items(): Q[k] += v/4
    for k, v in Pi.items(): Q[k[1:]] += v/4
    for k, v in Pr.items(): Q[k[1:]] += v/4
    for k, v in Pe.items(): Q[k[1:]] += v/4

    if mode == "instance":
        P = Pi
    elif mode == "relation":
        P = Pr
    elif mode == "entity":
        P = Pe
    else:
        raise ValueError("Invalid sampling mode {}".format(mode))

    p = precision(submission_id, P, Q)
    re = exhaustive_pooled_recall()
    rp = pooled_recall(submission_id, P, Q)
    r = re * rp
    logger.info("Pool recall is %.4f and recall on pool is %.4f; total is %.4f", re, rp, r)
    f1 = 2 * p * r / (p+r) if p+r > 0. else 0.
    return p, r, f1
