#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database schema as namedtuples
"""

from collections import namedtuple


_Provenance = namedtuple("Provenance", ["doc_id", "begin", "end"])
class Provenance(_Provenance):
    def __new__(cls, doc_id, begin, end):
        assert begin < end, "Invalid span, expected begin {} < end {}".format(begin, end)
        return super(Provenance, cls).__new__(cls, doc_id, begin, end)

MentionInstance = namedtuple("MentionInstance", ["id", "canonical_id", "type", "gloss", "weight"])
LinkInstance = namedtuple("LinkInstance", ["id", "link_name", "weight"])
RelationInstance = namedtuple("RelationInstance", ["subject_id", "object_id", "relation", "weight"])

EvaluationMentionResponse = namedtuple('EvaluationMentionResponse', [
    'assignment_id',
    'question_batch_id',
    'question_id',
    'doc_id',
    'mention_id',
    'canonical_id',
    'mention_type',
    'gloss',
    'weight'
])

EvaluationLinkResponse = namedtuple('EvaluationLinkResponse', [
    'assignment_id',
    'question_batch_id',
    'question_id',
    'doc_id',
    'mention_id',
    'link_name',
    'weight'
])

EvaluationRelationResponse = namedtuple('EvaluationRelationResponse', [
    'assignment_id',
    'question_batch_id',
    'question_id',
    'doc_id',
    'subject_id',
    'object_id',
    'relation',
    'weight'
])
