#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database schema as namedtuples
"""
import re
from collections import namedtuple

_Provenance = namedtuple("Provenance", ["doc_id", "begin", "end"])
class Provenance(_Provenance):
    def __new__(cls, doc_id, begin, end):
        assert begin <= end, "Invalid span, expected begin {} <= end {} for provenance {}:{}-{}".format(begin, end, doc_id, begin, end)
        return super(Provenance, cls).__new__(cls, doc_id, begin, end)

    def __str__(self):
        return "{}:{}-{}".format(self.doc_id, self.begin, self.end)

    @classmethod
    def from_str(cls, prov, inclusive=False):
        if len(prov) == 0:
            return None
        doc_id, beg, end =  re.match(r"([A-Za-z0-9_.]+):([0-9]+)-([0-9]+)", prov).groups()
        beg, end = int(beg), int(end)
        if inclusive:
            end += 1
        return cls(doc_id, beg, end)

MentionInstance = namedtuple("MentionInstance", ["doc_id", "span", "canonical_span", "mention_type", "gloss", "weight"])
LinkInstance = namedtuple("LinkInstance", ["doc_id", "span", "link_name", "correct", "weight"])
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

Score = namedtuple('Score', [
    'p', 'r', 'f1',
    'p_left', 'r_left', 'f1_left',
    'p_right', 'r_right', 'f1_right',
    ])
