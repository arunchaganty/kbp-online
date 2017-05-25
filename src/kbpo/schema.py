#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database schema as namedtuples
"""
from collections import namedtuple
from psycopg2.extras import NumericRange

_Provenance = namedtuple("Provenance", ["doc_id", "begin", "end"])
class Provenance(_Provenance):
    def __new__(cls, doc_id, begin, end):
        assert begin <= end, "Invalid span, expected begin {} <= end {} for provenance {}:{}-{}".format(begin, end, doc_id, begin, end)
        return super(Provenance, cls).__new__(cls, doc_id, begin, end)

def getNumericRange(begin, end):
    if begin >= end:
        raise IndexError(begin, end)
    return NumericRange(begin, end)


MentionInstance = namedtuple("MentionInstance", ["doc_id", "span", "canonical_span", "mention_type", "gloss", "weight"])
LinkInstance = namedtuple("LinkInstance", ["doc_id", "span", "link_name", "weight"])
RelationInstance = namedtuple("RelationInstance", ["doc_id", "subject", "object", "relation", "weight"])

EvaluationMentionResponse = namedtuple('EvaluationMentionResponse', [
    'assignment_id',
    'question_batch_id',
    'question_id',
    'doc_id',
    'span',
    'canonical_span',
    'mention_type',
    'gloss',
    'weight'
])

EvaluationLinkResponse = namedtuple('EvaluationLinkResponse', [
    'assignment_id',
    'question_batch_id',
    'question_id',
    'doc_id',
    'span',
    'link_name',
    'weight'
])

EvaluationRelationResponse = namedtuple('EvaluationRelationResponse', [
    'assignment_id',
    'question_batch_id',
    'question_id',
    'doc_id',
    'subject',
    'object',
    'relation',
    'weight'
])
