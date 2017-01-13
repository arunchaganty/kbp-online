#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read LDC's output format
"""

import numpy as np
import pandas as pd

class Provenance(object):
    def __init__(self, doc_id, start, end):
        self.doc_id = doc_id
        self.start = start
        self.end = end

    def __hash__(self):
        return hash(self.doc_id) ^ (self.start) ^ (self.end)

    def __lt__(self, other):
        if not isinstance(other, Provenance): raise AttributeError("Comparing {} with {}".format(self.__class__.__name__, other.__class__.__name__))
        return (self.doc_id, self.start, self.end) < (other.doc_id, other.start, other.end)

    def __le__(self, other):
        return (self == other) or (self < other)

    def __eq__(self, other):
        if not isinstance(other, Provenance): return False
        return self.doc_id == other.doc_id and self.start == other.start and self.end == other.end

    def __str__(self):
        return "{}:{}-{}".format(self.doc_id, self.start, self.end)

    @classmethod
    def from_str(cls, str_):
        doc_id, start_end = str_.split(':', 1)
        start, end = map(int, start_end.split('-', 1))
        return cls(doc_id, start, end)

    def __repr__(self):
        return "<Provenance:{}>".format(str(self))

def test_provenance_from_str():
    str_ = "ENG_NW_001278_20130214_F00011JDX:1448-1584"
    p = Provenance.from_str(str_)
    assert p.doc_id == "ENG_NW_001278_20130214_F00011JDX"
    assert p.start == 1448
    assert p.end == 1584

def test_provenance_cmp():
    p1 = Provenance("A", 10, 20)
    p2 = Provenance("A", 10, 20)
    p3 = Provenance("A", 15, 24)
    p4 = Provenance("B", 10, 20)

    assert p1 == p2
    assert p1 <= p2
    assert p1 < p3
    assert p3 > p1
    assert p1 < p4

class EvaluationEntry(object):
    def __init__(self, id_, query_id, relation, relation_provenances, slot_value, slot_provenances, slot_value_label, relation_label, eq_class):
        self.id = id_
        self.query_id = query_id
        self.relation = relation
        self.relation_provenances = relation_provenances
        self.slot_value = slot_value
        self.slot_provenances = slot_provenances
        self.slot_value_label = slot_value_label
        self.relation_label = relation_label
        self.eq_class = eq_class

    def __str__(self):
        return "{}: {} {} {}".format(self.id, self.query_id, self.relation, self.slot_value)

    def __repr__(self):
        return "<Entry: {}>".format(str(self))

    @classmethod
    def from_line(cls, line):
        parts = line.split("\t")
        id_ = parts[0]
        query_id, relation = parts[1].split(':', 1)
        relation_provenances = [Provenance.from_str(s) for s in parts[2].split(',')]
        slot_value = parts[3]
        slot_provenances = [Provenance.from_str(s) for s in parts[4].split(',')]
        slot_value_label = parts[5]
        relation_label = parts[6]
        eq_class = parts[7]
        return cls(id_, query_id, relation, relation_provenances, slot_value, slot_provenances, slot_value_label, relation_label, eq_class)

    def to_list(self):
        return [
            self.query_id,
            self.relation,
            self.slot_value,
            self.slot_value_label,
            self.relation_label,
            self.eq_class,]

    @classmethod
    def to_pandas(cls, entries):
        """
        Convert a set of entries to pandas.
        """
        X = np.array([entry.to_list() for entry in entries])
        return pd.DataFrame(X, index=[entry.id for entry in entries], columns="query_id relation slot_value slot_value_label relation_label eq_class".split())

def test_evaluation_entry():
    line = "CS15_ENG_0016_0_001	CS15_ENG_0016:gpe:births_in_country	ENG_NW_001278_20130214_F00011JDX:1448-1584	Agriculture	ENG_NW_001278_20130214_F00011JDX:1505-1515	W	W	0"
    entry = EvaluationEntry.from_line(line)
    assert entry.id == "CS15_ENG_0016_0_001"
    assert entry.query_id == "CS15_ENG_0016"
    assert entry.relation == "gpe:births_in_country"
    assert entry.relation_provenances == [Provenance("ENG_NW_001278_20130214_F00011JDX", 1448, 1584)]
    assert entry.slot_value == "Agriculture"
    assert entry.slot_provenances == [Provenance("ENG_NW_001278_20130214_F00011JDX", 1505, 1515)]
    assert entry.slot_value_label == "W"
    assert entry.relation_label == "W"
    assert entry.eq_class == "0"

class OutputEntry(object):
    def __init__(self, query_id, relation, run_id, relation_provenances, slot_value, slot_type, slot_provenances, confidence):
        self.query_id = query_id
        self.relation = relation
        self.run_id = run_id
        self.relation_provenances = relation_provenances
        self.slot_value = slot_value
        self.slot_type = slot_type
        self.slot_provenances = slot_provenances
        self.confidence = confidence

    @classmethod
    def from_line(cls, line):
        parts = line.split("\t")
        query_id = parts[0]
        relation = parts[1]
        run_id = parts[2]
        relation_provenances = [Provenance.from_str(s) for s in parts[3].split(',')]
        slot_value = parts[4]
        slot_type = parts[5]
        slot_provenances = [Provenance.from_str(s) for s in parts[6].split(',')]
        confidence = float(parts[7])
        return cls(query_id, relation, run_id, relation_provenances, slot_value, slot_type, slot_provenances, confidence)

def test_output_entry():
    line = "CSSF15_ENG_001e2aa16f	gpe:births_in_city	KB_BBN1	NYT_ENG_20130513.0090:2476-2540	Kenneth Everette Battelle	PER	NYT_ENG_20130513.0090:2476-2500	0.9"
    entry = OutputEntry.from_line(line)
    assert entry.query_id == "CSSF15_ENG_001e2aa16f"
    assert entry.relation == "gpe:births_in_city"
    assert entry.run_id == "KB_BBN1"
    assert entry.relation_provenances == [Provenance("NYT_ENG_20130513.0090",2476,2540)]
    assert entry.slot_value == "Kenneth Everette Battelle"
    assert entry.slot_type == "PER"
    assert entry.slot_provenances == [Provenance("NYT_ENG_20130513.0090", 2476,2500)]
    assert entry.confidence == 0.9
