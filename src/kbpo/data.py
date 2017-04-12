"""
Utilities to manage different data input files.
"""
import logging
from collections import namedtuple

from tqdm import tqdm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Provenance(namedtuple("Provenance", ["doc_id", "start", "end"])):
    @classmethod
    def from_str(cls, str_):
        doc_id, start_end = str_.split(':', 1)
        start, end = map(int, start_end.split('-', 1))
        return cls(doc_id, start, end)

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

class EvaluationEntry(namedtuple("EvaluationEntry", ["id", "query_id", 'ldc_id', "relation", "relation_provenances", "slot_value", "slot_provenances", "slot_value_label", "relation_label", "eq_class", "eq"])):
    def __str__(self):
        return "{}: {} {} {}".format(self.id, self.query_id, self.relation, self.slot_value)

    def __repr__(self):
        return "<Entry: {}>".format(str(self))

    @classmethod
    def from_line(cls, line):
        parts = line.split("\t")
        id_ = parts[0]
        query_id, relation = parts[1].split(':', 1)
        ldc_id = None
        relation_provenances = [Provenance.from_str(s) for s in parts[2].split(',')]
        slot_value = parts[3]
        slot_provenances = [Provenance.from_str(s) for s in parts[4].split(',')]
        slot_value_label = parts[5]
        relation_label = parts[6]
        eq_class = parts[7]
        eq = int(parts[7].split(":")[-1])
        return cls(id_, query_id, ldc_id, relation, relation_provenances, slot_value, slot_provenances, slot_value_label, relation_label, eq_class, eq)

    def to_list(self):
        return [
            self.query_id,
            self.relation,
            self.slot_value,
            self.slot_value_label,
            self.relation_label,
            self.eq_class,]

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

class OutputEntry(namedtuple("EvaluationEntry", ["query_id", "ldc_id", "relation", "run_id", "relation_provenances", "slot_value", "slot_type", "slot_provenances", "confidence"])):
    @classmethod
    def from_line(cls, line):
        parts = line.split("\t")
        query_id = parts[0]
        ldc_id = None
        relation = parts[1]
        run_id = parts[2]
        relation_provenances = [Provenance.from_str(s) for s in parts[3].split(',')]
        slot_value = parts[4]
        slot_type = parts[5]
        slot_provenances = [Provenance.from_str(s) for s in parts[6].split(',')]
        confidence = float(parts[7])
        return cls(query_id, ldc_id, relation, run_id, relation_provenances, slot_value, slot_type, slot_provenances, confidence)

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

def load_queries(fstream):
    Q = {}
    for line in fstream:
        fields = line.split()
        # NOTE: We are considering partial assessments because that's
        # what KBP is doing too.
        ldc_query, cssf_query = fields[:2]
        Q[cssf_query] = ldc_query
    return Q

def load_gold(fstream, Q):
    gold = []
    for line in tqdm(fstream):
        entry = EvaluationEntry.from_line(line)
        if entry.query_id in Q:
            gold.append(entry._replace(ldc_id=Q[entry.query_id]))
    logger.info("Loaded %d evaluation entries", len(gold))
    return gold

def load_output(fstream, Q):
    output = []
    for line in tqdm(fstream):
        entry = OutputEntry.from_line(line)
        if entry.query_id in Q:
            output.append(entry._replace(ldc_id=Q[entry.query_id]))
    logger.info("Loaded %d output entries.", len(output))
    return output
