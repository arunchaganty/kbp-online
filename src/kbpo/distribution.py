"""
Various distributions from the database.
"""
import logging
from collections import Counter, defaultdict

from . import db
from .api import get_submissions, get_submission

logger = logging.getLogger(__name__)

# TODO: This seems fishy.
#def compute_exhaustive_distribution(corpus_tag):
#    distribution = Counter()
#    for row in db.select("""
#        WITH _counts AS (
#            SELECT COUNT(*) FROM evaluation_relation e, evaluation_batch b
#            WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations' AND b.corpus_tag = %(tag)s)
#        SELECT subject_id, relation, object_id, 1./c.count AS prob 
#        FROM evaluation_relation e, evaluation_batch b, _counts c
#        WHERE e.question_batch_id = b.id AND b.batch_type = 'exhaustive_relations'
#          AND b.corpus_tag = %(tag)s
#        """, tag=corpus_tag):
#        distribution[row.subject_id, row.relation, row.object_id] = float(row.prob)
#    return distribution
#
#def test_compute_exhaustive_distribution():
#    tag = 'kbp2016'
#    distribution = compute_exhaustive_distribution(tag)
#    value = sum(distribution.values())
#    assert abs(value - 1.0) < 1.e-5, "Distribution is not normalized: Z = {}".format(value)

# Get distributions.
def submission_instance(corpus_tag, submission_id=None):
    if submission_id is not None:
        assert get_submission(submission_id).corpus_tag == corpus_tag, "Submission {} is not on corpus {}".format(submission_id, corpus_tag)
        where = "WHERE s.submission_id = %(submission_id)s"
    else:
        where = ""

    distribution = defaultdict(Counter)
    for row in db.select("""
        WITH _counts AS (
            SELECT submission_id, COUNT(*)
            FROM submission_relation s
            JOIN submission s_ ON (s_.id = s.submission_id AND s_.corpus_tag = %(corpus_tag)s)
            {where}
            GROUP BY submission_id
            )
        SELECT s.submission_id, s.doc_id, s.subject, s.object, 1./c.count AS prob
        FROM submission_relation s
        JOIN submission s_ ON (s_.id = s.submission_id AND s_.corpus_tag = %(corpus_tag)s)
        JOIN _counts c ON (s.submission_id = c.submission_id)
        {where}
        """.format(where=where), corpus_tag=corpus_tag, submission_id=submission_id):
        distribution[row.submission_id][row.doc_id, (row.subject.lower, row.subject.upper), (row.object.lower, row.object.upper)] = float(row.prob)
    return distribution

def test_submission_instance():
    tag = 'kbp2016'
    Ps = submission_instance(tag)
    for submission in get_submissions(tag):
        Z = sum(Ps[submission.id].values())
        assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def test_submission_instance_with_id():
    tag = 'kbp2016'
    submission = next(get_submissions(tag))
    Ps = submission_instance(tag, submission.id)
    assert len(Ps) == 1 and submission.id in Ps
    P = Ps[submission.id]
    Z = sum(P.values())
    assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def submission_relation(corpus_tag, submission_id=None):
    if submission_id is not None:
        assert get_submission(submission_id).corpus_tag == corpus_tag, "Submission {} is not on corpus {}".format(submission_id, corpus_tag)
        where = "WHERE s.submission_id = %(submission_id)s"
    else:
        where = ""

    distribution = defaultdict(Counter)
    for row in db.select("""
        WITH _counts AS (
            SELECT submission_id, relation, COUNT(*) 
            FROM submission_relation s
            JOIN submission s_ ON (s_.id = s.submission_id AND s_.corpus_tag = %(corpus_tag)s)
            {where}
            GROUP BY submission_id, relation),
            _relation_counts AS (SELECT submission_id, COUNT(*) FROM _counts GROUP BY submission_id)
        SELECT s.submission_id, s.doc_id, s.subject, s.object, (1./c.count)/(r.count) AS prob
        FROM submission_relation s
        JOIN submission s_ ON (s_.id = s.submission_id AND s_.corpus_tag = %(corpus_tag)s)
        JOIN _counts c ON (s.submission_id = c.submission_id AND s.relation = c.relation)
        JOIN _relation_counts r ON (s.submission_id = r.submission_id)
        {where}
        """.format(where=where), corpus_tag=corpus_tag, submission_id=submission_id):
        distribution[row.submission_id][row.doc_id, (row.subject.lower, row.subject.upper), (row.object.lower, row.object.upper)] = float(row.prob)
    return distribution

def test_submission_relation():
    tag = 'kbp2016'
    Ps = submission_relation(tag)
    for submission in get_submissions(tag):
        Z = sum(Ps[submission.id].values())
        assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def test_submission_relation_by_id():
    tag = 'kbp2016'
    submission = next(get_submissions(tag))
    Ps = submission_relation(tag, submission.id)
    assert len(Ps) == 1 and submission.id in Ps
    P = Ps[submission.id]
    Z = sum(P.values())
    assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def submission_entity(corpus_tag, submission_id=None):
    if submission_id is not None:
        assert get_submission(submission_id).corpus_tag == corpus_tag, "Submission {} is not on corpus {}".format(submission_id, corpus_tag)
        where = "WHERE s.submission_id = %(submission_id)s"
    else:
        where = ""

    distribution = defaultdict(Counter)
    for row in db.select("""
        WITH _counts AS (
                SELECT s.submission_id, COALESCE(l.link_name, n.gloss) AS link_name, COUNT(*) 
                FROM submission_relation s
                JOIN submission s_ ON (s_.id = s.submission_id AND s_.corpus_tag = %(corpus_tag)s)
                JOIN submission_mention m ON (s.submission_id = m.submission_id AND s.doc_id = m.doc_id AND s.subject = m.span)
                JOIN submission_mention n ON (s.submission_id = n.submission_id AND s.doc_id = n.doc_id AND m.canonical_span = n.span)
                LEFT OUTER JOIN submission_link l ON (s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND m.canonical_span = l.span)
                {where}
                GROUP BY COALESCE(l.link_name, n.gloss), s.submission_id),
             _entity_counts AS ( SELECT submission_id, COUNT(*) FROM _counts GROUP BY submission_id)
        SELECT s.submission_id, s.doc_id, s.subject, s.object, l.link_name, (1./c.count)/(e.count) AS prob
        FROM submission_relation s
        JOIN submission s_ ON (s_.id = s.submission_id AND s_.corpus_tag = %(corpus_tag)s)
        JOIN submission_mention m ON (s.submission_id = m.submission_id AND s.doc_id = m.doc_id AND s.subject = m.span)
        JOIN submission_mention n ON (s.submission_id = n.submission_id AND s.doc_id = n.doc_id AND m.canonical_span = n.span)
        LEFT OUTER JOIN submission_link l ON (s.submission_id = l.submission_id AND s.doc_id = l.doc_id AND m.canonical_span = l.span)
        JOIN _counts c ON (s.submission_id = c.submission_id AND c.link_name = COALESCE(l.link_name, m.gloss))
        JOIN _entity_counts e ON (s.submission_id = e.submission_id)
        {where}
        """.format(where=where), corpus_tag=corpus_tag, submission_id=submission_id):
        distribution[row.submission_id][row.doc_id, (row.subject.lower, row.subject.upper), (row.object.lower, row.object.upper)] = float(row.prob)
    return distribution

def test_submission_entity():
    tag = 'kbp2016'
    Ps = submission_entity(tag)
    for submission in get_submissions(tag):
        Z = sum(Ps[submission.id].values())
        assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)

def test_submission_entity_by_id():
    tag = 'kbp2016'
    submission = next(get_submissions(tag))
    Ps = submission_entity(tag, submission.id)
    assert len(Ps) == 1 and submission.id in Ps
    P = Ps[submission.id]
    Z = sum(P.values())
    assert abs(Z - 1.0) < 1.e-5, "Distribution for {} is not normalized: Z = {}".format(submission.id, Z)
