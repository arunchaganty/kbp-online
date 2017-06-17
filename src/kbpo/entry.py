"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import pdb
import gzip
import os
import re
import csv
import logging
from collections import namedtuple, defaultdict

from tqdm import tqdm

from .defs import TYPES, RELATION_MAP, ALL_RELATIONS, INVERTED_RELATIONS, STRING_VALUED_RELATIONS, VALID_MENTION_TYPES, RELATION_TYPES, standardize_relation
from .schema import Provenance

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

class ListLogger():
    def __init__(self):
        self.warnings = defaultdict(list)
        self.errors = defaultdict(list)
        self.infos = defaultdict(list)

    #Assumes the text to be of the form (Line %d: <error_msg>)
    def _message(self, type_, text, *args):
        if isinstance(args[0], int) and text.find(":") > 0:
            line_no = args[0]
            text = text%(args)
            parts = text.split(":", 2)
            if len(parts) == 2:
                cat, text = "General", parts[1]
            else:
                cat, text  = parts[1], parts[2]
            type_[cat].append((line_no, text))

    def warning(self, text, *args):
        self._message(self.warnings, text, *args)
    def error(self, text, *args):
        self._message(self.errors, text, *args)
    def info(self, text, *args):
        self._message(self.infos, text, *args)

    def __str__(self):
        return str(self.errors) + str(self.warnings) + str(self.info)

class Entry(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'weight', 'lineno'])):
    @property
    def pair(self):
        return (self.subj, self.obj)

    @property
    def inv_pair(self):
        return (self.obj, self.subj)

class MFile(namedtuple('_MFile', ['types', 'links', 'canonical_mentions', 'relations'])):
    def __new__(cls, types, links, cmentions, relations):
        self = super(MFile, cls).__new__(cls, types, links, cmentions, relations)
        self._type_map = {row.subj: row.reln for row in types}
        self._gloss_map = {row.subj: row.obj for row in types}
        self._link_map = {row.subj: row.obj for row in links}
        self._cmention_map = {row.subj: row.obj for row in cmentions}
        self.mention_ids = set(row.subj for row in self.types)
        return self

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new A object from a sequence or iterable'
        result = super(MFile, cls)._make(iterable, new, len)
        return cls.__new__(cls, *result)

    def get_gloss(self, m_id):
        return self._gloss_map.get(m_id)
    def get_type(self, m_id):
        return self._type_map.get(m_id)
    def get_link(self, m_id):
        return self._cmention_map.get(m_id) and  self._link_map.get(self._cmention_map.get(m_id))
    def get_cmention(self, m_id):
        return self._cmention_map.get(m_id)

    def normalize_relation(self, entry):
        subj_, _, reln_, obj_, _ = standardize_relation(entry.subj, self.get_type(entry.subj), entry.reln, entry.obj, self.get_type(entry.obj))
        return entry._replace(subj=subj_, reln=reln_, obj=obj_)

    def write(self, fstream):
        writer = csv.writer(fstream, delimiter="\t")
        for row in self.types:
            writer.writerow([str(row.subj), row.reln, row.obj, row.prov, row.weight])
        for row in self.links:
            writer.writerow([str(row.subj), row.reln, row.obj, row.prov, row.weight])
        for row in self.canonical_mentions:
            writer.writerow([str(row.subj), row.reln, str(row.obj), row.prov, row.weight])
        for row in self.relations:
            writer.writerow([str(row.subj), row.reln, str(row.obj), ",".join([str(p) for p in row.prov]), row.weight])

class MFileReader(object):
    def __init__(self):
        self.logger = None
        self._types = None
        self._links = None
        self._glosses = None
        self._cmentions = None
        self._relations = None
        self._provenances = None
        self._weights = None
    
    def _add_mention(self, row):
        """
        Adds a mention to the type and gloss dictionaries.
        """
        assert row.reln in TYPES

        if row.subj in self._types:
            if row.reln != self._types[row.subj]:
                self.logger.error("LINE %d: Inconsistent mention type: %s -> %s (earlier: %s)", row.lineno, row.subj, row.reln, self._types[row.subj])
            elif row.obj != self._glosses[row.subj]:
                self.logger.error("LINE %d: Inconsistent mention gloss: %s -> %s (earlier: %s)", row.lineno, row.subj, row.obj, self._glosses[row.subj])
            else:
                self.logger.warning("LINE %d: Duplicate mention definition: %s", row.lineno, row)
        else:
            self._types[row.subj] = row.reln
            self._glosses[row.subj] = row.obj

    def _add_cmention(self, row):
        assert row.reln == "canonical_mention"

        if row.subj in self._cmentions:
            if row.obj != self._cmentions[row.subj]:
                self.logger.error("LINE %d: Inconsistent canonical mention: %s -> %s (earlier: %s)", row.lineno, row.subj, row.obj, self._cmentions[row.subj])
            else:
                self.logger.warning("LINE %d: Duplicate canonical mention definition: %s", row.lineno, row)
        else:
            self._cmentions[row.subj] = row.obj
            self._weights[row.subj, 'cmention'] = row.weight

    def _add_link(self, row):
        assert row.reln == "link"

        if row.subj in self._links:
            if row.obj != self._links[row.subj]:
                self.logger.error("LINE %d: Inconsistent link: %s -> %s (earlier: %s)", row.lineno, row.subj, row.obj, self._links[row.subj])
            else:
                self.logger.warning("LINE %d: Duplicate link definition: %s", row.lineno, row)
        else:
            if row.obj.startswith("NILX"):
                self.logger.warning("LINE %d: Using reserved NILX linkspace: %s", row.lineno, row)
            self._links[row.subj] = row.obj
            self._weights[row.subj, 'link'] = row.weight

    def _add_relation(self, row):
        assert row.reln in ALL_RELATIONS

        if (row.subj, row.obj) in self._relations:
            if row.reln != self._relations[row.subj, row.obj]:
                self.logger.error("LINE %d: Inconsistent relation definition: (%s,%s) -> %s (earlier: %s)", row.lineno, row.subj, row.obj, row.reln, self._relations[row.subj, row.obj])
            else:
                self.logger.warning("LINE %d: Duplicate relation definition: %s", row.lineno, row)
        else:
            if len(row.prov) == 0:
                self.logger.warning("LINE %d: Missing relation provenance, using between-mention span: %s", row.lineno, row)
                self.prov = (Provenance(row.subj.doc_id, min(row.subj.begin, row.obj.begin), max(row.subj.end, row.obj.end),))
            self._relations[row.subj, row.obj] = row.reln
            self._provenances[row.subj, row.obj] = row.prov
            self._weights[row.subj, row.obj] = row.weight

    def _check_doc_ids(self, row, doc_ids=None):
        if doc_ids is not None and row.subj.doc_id not in doc_ids:
            self.logger.warning("LINE %d: Ignoring mention outside corpus: %s", row.lineno, row)
            return False
        elif row.reln == "canonical_mention" and row.subj.doc_id != row.obj.doc_id:
            self.logger.error("LINE %d: Canonical mention outside mention document: %s", row.lineno, row)
            return False
        elif row.reln in ALL_RELATIONS:
            if row.subj.doc_id != row.obj.doc_id:
                self.logger.error("LINE %d: object mention outside subject mention document: %s", row.lineno, row)
                return False
            elif any(row.subj.doc_id != p.doc_id for p in row.prov):
                self.logger.error("LINE %d: provenance outside mention document: %s", row.lineno, row)
                return False
        return True

    def _verify_mentions_defined(self):
        nil_count = 0
        for m in self._types:
            assert m in self._glosses
            if m not in self._cmentions:
                self.logger.warning("LINE %d: Missing canonical mention definition: Making %s a canonical mention", 0, m)
                self._cmentions[m] = m
                self._weights[m, "cmention"] = 0.0
            if m not in self._links:
                link = "NILX{}".format(nil_count)
                self.logger.warning("LINE %d: Missing link definition: Making %s link to %s", 0, m, link)
                self._links[m] = link
                self._weights[m, "link"] = 0.0

        purge = set()
        for m, n in self._cmentions.items():
            if m not in self._types:
                self.logger.error("LINE %d: Ignoring canonical_mention with missing mention: %s (in %s canonical_mention %s)", 0, m, m, n)
                purge.add(m)
            if n not in self._types:
                self.logger.error("LINE %d: Ignoring canonical_mention with missing mention: %s (in %s canonical_mention %s)", 0, n, m, n)
                purge.add(m)
        for m in purge:
            del self._cmentions[m]
            del self._weights[m, 'cmention']

        purge = set()
        for m, n in self._links.items():
            if m not in self._types:
                self.logger.error("LINE %d: Ignoring link with missing mention: %s (in %s link %s)", 0, m, m, n)
                purge.add(m)
        for m in purge:
            del self._links[m]
            del self._weights[m, 'link']

        purge = set()
        for (m, n), r in self._relations.items():
            if m not in self._types:
                self.logger.error("LINE %d: Ignoring relation with missing mention: %s (in %s %s %s)", 0, m, m, r, n)
                purge.add((m,n))
            if n not in self._types:
                self.logger.error("LINE %d: Ignoring relation with missing mention: %s (in %s %s %s)", 0, n, m, r, n)
                purge.add((m,n))
        for mn in purge:
            del self._relations[mn]
            del self._provenances[mn]
            del self._weights[mn]

    def _verify_relation_types(self):
        purge = set()
        for (m, n), r in self._relations.items():
            if (self._types[m], self._types[n]) not in VALID_MENTION_TYPES:
                self.logger.error("LINE %d: Inconsistent relation argument types: %s(%s) %s %s(%s) (execpted %s -> %s)",
                                  0, m, self._types[m], r, n, self._types[n], n, *RELATION_TYPES[r])
                purge.add((m,n))
        for mn in purge:
            del self._relations[mn]

    def _verify_symmetrized_relations(self):
        add, add_prov, add_weights = dict(), dict(), dict()

        for (m, n), r in self._relations.items():
            if r in INVERTED_RELATIONS:
                for r_ in INVERTED_RELATIONS[r]:
                    if r_.startswith(self._types[n].lower()):
                        if (n, m) not in self._relations and (n, m) not in add:
                            self.logger.warning("LINE %d: Adding symmetrized relation: %s %s %s", 0, n, r_, m)
                            add[n,m] = r_
                            add_prov[n,m] = self._provenances[m,n]
                            add_weights[n,m] = self._weights[m,n]
                        elif (n, m) in self._relations and self._relations[n,m] != r_:
                            self.logger.error("LINE %d: Inconsistent symmetric relations: %s %s %s symmetrized conflicts with %s %s %s", 0, m, r, n, n, self._relations[n,m], m)
                        elif (n, m) in add and add[n,m] != r_:
                            self.logger.error("LINE %d: Inconsistent symmetric relations: %s %s %s symmetrized conflicts with %s %s %s", 0, m, r, n, n, add[n,m], m)
        for (n, m), r in add.items():
            self._relations[n,m] = r
            self._provenances[n,m] = add_prov[n,m]
            self._weights[n,m] = add_weights[n,m]

    def _build(self):
        """
        Constructs the final MFile from intermediate stuff
        """
        mentions, cmentions, links, relations = [], [], [], []
        for m, t in sorted(self._types.items()):
            mentions.append(Entry(m, t, self._glosses[m], None, None, None))
            cmentions.append(Entry(m, 'canonical_mention', self._cmentions[m], None, self._weights[m, 'cmention'], None))
            links.append(Entry(m, 'link', self._links[m], None, self._weights[m, 'link'], None))

        for (m, n), r in sorted(self._relations.items()):
            relations.append(Entry(m, r, n, self._provenances[m,n], self._weights[m, n], None))

        return MFile(mentions, links, cmentions, relations)

    def _validate(self):
        self._verify_mentions_defined()
        self._verify_relation_types()
        self._verify_symmetrized_relations()

    def parse(self, fstream, doc_ids=None, logger=_logger):
        """
        Parses (and validates) an m-file in the file stream @fstream.
        """
        reader = csv.reader(fstream, delimiter="\t")

        self.logger = logger
        self._types = dict()
        self._links = dict()
        self._glosses = dict()
        self._cmentions = dict()
        self._relations = dict()
        self._provenances = dict()
        self._weights = dict()

        # First pass of the data that builds the above tables.
        for lineno, row in enumerate(tqdm(reader)):
            if len(row) == 0: continue # Skip empty lines
            if len(row) > 5:
                logger.error("LINE %d: Invalid number of columns, %d instead of %d", lineno, len(row), 5)
                continue
            row = row + [None] * (5-len(row)) + [lineno,]
            row = Entry(*row)
            row = row._replace(subj = Provenance.from_str(row.subj), weight = float(row.weight) if row.weight else 0.0)

            if row.reln in TYPES:
                if self._check_doc_ids(row):
                    self._add_mention(row)
            elif row.reln == "link":
                if self._check_doc_ids(row):
                    self._add_link(row)
            elif row.reln == "canonical_mention":
                row = row._replace(obj = Provenance.from_str(row.obj))
                if self._check_doc_ids(row):
                    self._add_cmention(row)
            elif row.reln in RELATION_MAP:
                provs = tuple(Provenance.from_str(p.strip()) for p in row.prov.split(',') if p)
                row = row._replace(reln=RELATION_MAP[row.reln], obj = Provenance.from_str(row.obj), prov=provs)
                if self._check_doc_ids(row):
                    self._add_relation(row)
            else:
                logger.warning("LINE %d: Ignoring relation: %s (not supported)", row.lineno, row.reln)

        return self._build()

class TacKbReader(MFileReader):
    def __init__(self):
        MFileReader.__init__(self)

        # intermediate stuff.
        self._entity_mentions = None
        self._entity_cmentions = None
        self._entity_types = None
        self._entity_relations = None

    def _add_entity_mention(self, row):
        assert row.reln == "mention" or row.reln == "canonical_mention"

        if row.prov in self._glosses and self._glosses[row.prov] != row.obj:
            self.logger.error("LINE %d: Inconsistent mention definition: %s (earlier %s %s)", row.lineno, row, row.prov, self._glosses[row.prov])
        else:
            self._entity_mentions[row.subj, row.prov.doc_id].append(row.prov)
            self._glosses[row.prov] = row.obj

    def _add_entity_cmention(self, row):
        assert row.reln == "canonical_mention"

        if (row.subj, row.prov.doc_id) in self._entity_cmentions and self._entity_cmentions[row.subj, row.prov.doc_id] != row.prov:
            prov_ = self._entity_cmentions[row.subj, row.prov.doc_id]
            self.logger.error("LINE %d: Inconsistent canonical mention definition: %s (earlier %s %s)", row.lineno, row, prov_, self._glosses[prov_])
        else:
            self._entity_cmentions[row.subj, row.prov.doc_id] = row.prov
        self._add_entity_mention(row)

    def _add_entity_type(self, row):
        assert row.reln == "type"

        if row.subj in self._entity_types and self._entity_types[row.subj] != row.obj:
            self.logger.error("LINE %d: Inconsistent type definition: %s (earlier %s)", row.lineno, row, self._entity_types[row.subj])
        else:
            self._entity_types[row.subj] = row.obj

    def _add_entity_relation(self, row):
        assert row.reln in ALL_RELATIONS
        self._entity_relations[row.subj, row.obj].append(row)

    def _verify_types(self):
        # check that all entities' types have been defined.
        purge = set()
        for entity, doc_id in self._entity_mentions:
            if entity not in self._entity_types:
                self.logger.error("LINE %d: Type not found for entity %s", 0, entity)
                purge.add((entity, doc_id))
        for entity, doc_id in purge:
            for m in self._entity_mentions[entity, doc_id]:
                del self._glosses[m]
            del self._entity_mentions[entity, doc_id]

        purge = set()
        for entity, doc_id in self._entity_cmentions:
            if entity not in self._entity_types:
                self.logger.error("LINE %d: Type not found for entity %s", 0, entity)
                purge.add((entity, doc_id))
        for entity, doc_id in purge:
            del self._entity_cmentions[entity, doc_id]

        purge = set()
        for (subject, object_), rows in self._entity_relations.items():
            is_string_relation = any(row.reln in STRING_VALUED_RELATIONS for row in rows)
            if subject not in self._entity_types:
                self.logger.error("LINE %d: Type not found for entity %s", 0, subject)
                purge.add((subject, object_))
            if not is_string_relation and object_ not in self._entity_types:
                self.logger.error("LINE %d: Type not found for entity %s", 0, object_)
                purge.add((subject, object_))
        for entity, doc_id in purge:
            del self._entity_relations[subject, object_]

    def _verify_cmentions(self):
        # check that all mentions in a document have atleast one canonical mention.
        for entity, doc_id in self._entity_mentions:
            for m in self._entity_mentions[entity, doc_id]: # contains every mention.
                if (entity, m.doc_id) not in self._entity_cmentions:
                    self.logger.warning("LINE %d: Missing canonical mention in document: not found for entity %s in document %s; using %s instead", 0, entity, m.doc_id, m)
                    self._entity_cmentions[entity, m.doc_id] = m


    def _find_first_contained_mention(self, entity, prov):
        for m in self._entity_mentions[entity, prov.doc_id]:
            if m.begin >= prov.begin and m.end <= prov.end:
                return m

    def _find_first_overlapping_mention(self, entity, prov):
        for m in self._entity_mentions[entity, prov.doc_id]:
            if (m.begin >= prov.begin and m.begin <= prov.end) or \
                    (m.end >= prov.begin and m.end <= prov.end):
                return m

    def _find_first_subsequent_mention(self, entity, prov):
        for m in self._entity_mentions[entity, prov.doc_id]:
            if m.begin >= prov.begin:
                return m

    def _resolve_arguments(self, row, resolution_method=None):
        """
        Resolve arguments for row by searching through mentions near provenance.
        """
        if resolution_method is None:
            resolution_method = self._find_first_subsequent_mention

        if row.reln in STRING_VALUED_RELATIONS:
            """
            The provenance gives us the string value.
            """
            object_prov = row.prov[0]
            object_gloss = row.obj
            object_type = STRING_VALUED_RELATIONS[row.reln]

            # Add a new mention for this object (won't be seen anywhere
            # else)
            if (object_prov.end - object_prov.begin) != len(object_gloss):
                self.logger.warning("LINE %d: Provenance does not match string: %s (%d characters) maps to %s (%d characters)",
                                    0, object_prov, object_prov.end - object_prov.begin, object_gloss, len(object_gloss))

            # TODO: Check for inconsistency here?
            self._types[object_prov] = object_type
            self._glosses[object_prov] = object_gloss
            self._cmentions[object_prov] = object_prov
            self._weights[object_prov, 'cmention'] = 0.0
            self._links[object_prov] = object_prov
            self._weights[object_prov, 'link'] = 0.0

            for prov in row.prov[1:]:
                subject_prov = resolution_method(row.subj, prov)
                if subject_prov is not None: break
            else:
                self.logger.error("LINE %d: Could not find provenance for subject: %s", row.lineno, row)
                return
        else:
            for prov in row.prov:
                subject_prov = resolution_method(row.subj, prov)
                if subject_prov is not None: break
            else:
                self.logger.error("LINE %d: Could not find provenance for subject: %s", row.lineno, row)
                return

            for prov in row.prov:
                object_prov = resolution_method(row.obj, prov)
                if object_prov is not None: break
            else:
                self.logger.error("LINE %d: Could not find provenance for object: %s", row.lineno, row)
                return

        self._relations[subject_prov, object_prov] = row.reln
        self._provenances[subject_prov, object_prov] = row.prov
        self._weights[subject_prov, object_prov] = row.weight

    def _resolve_relations(self, resolution_method=None):
        if resolution_method is None:
            resolution_method = self._find_first_subsequent_mention

        for relations in tqdm(self._entity_relations.values(), desc="resolving entity relations"):
            for row in relations:
                self._resolve_arguments(row)

    def _validate(self):
        self._verify_types()
        self._verify_cmentions()
        self._resolve_relations()

    def _build(self):
        # Add mentions
        for (entity, doc_id), mentions in self._entity_mentions.items():
            entity_type = self._entity_types[entity]
            for m in mentions:
                self._types[m] = entity_type
                # _glosses already handled.
                self._cmentions[m] = self._entity_cmentions[entity, m.doc_id]
                self._links[m] = entity

        MFileReader._validate(self)
        return MFileReader._build(self)

    def parse(self, fstream, doc_ids=None, logger=_logger):
        reader = csv.reader(fstream, delimiter="\t")

        self.logger = logger
        # intermediate stuff.
        self._entity_mentions = defaultdict(list)
        self._entity_cmentions = dict()
        self._entity_types = dict()
        self._entity_relations = defaultdict(list)

        # Used in final outpuT
        self._types = dict()
        self._glosses = dict()
        self._cmentions = dict()
        self._links = dict()
        self._relations = dict()
        self._provenances = dict()
        self._weights = dict()

        # First pass of the data that builds the above tables.
        for lineno, row in enumerate(tqdm(reader)):
            if lineno == 0: continue # skip system header
            if len(row) == 0: continue # skip empty lines

            if len(row) > 5:
                self.logger.error("LINE %d: Invalid number of columns, %d instead of %d", lineno, len(row), 5)
                continue

            row = row + [None] * (5-len(row)) + [lineno,]
            row = Entry(*row)
            row = row._replace(weight = float(row.weight) if row.weight else 0.0)
            if row.reln == 'mention':
                if row.prov is None:
                    self.logger.error("LINE %d: No provenance for mention: %s", row.lineno, row)
                    continue
                row = row._replace(prov=Provenance.from_str(row.prov))
                self._add_entity_mention(row)
            elif row.reln == 'canonical_mention':
                if row.prov is None:
                    self.logger.error("LINE %d: No provenance for mention: %s", row.lineno, row)
                    continue
                row = row._replace(prov=Provenance.from_str(row.prov))
                self._add_entity_cmention(row)
            elif row.reln == 'type':
                self._add_entity_type(row)
            elif row.reln in RELATION_MAP:
                row = row._replace(reln=RELATION_MAP[row.reln], prov=tuple(Provenance.from_str(p.strip()) for p in row.prov.split(",")))
                self._add_entity_relation(row)
            else:
                self.logger.warning("LINE %d: Ignoring relation: %s (not supported)", row.lineno, row.reln)
        self._validate()
        return self._build()

def test_validate_mfile():
    testdir = os.path.join(os.path.dirname(__file__), "testdata")
    logger = ListLogger()
    reader = MFileReader()

    with open(os.path.join(testdir, "test_mfile_duplicate.m")) as f:
        mfile = reader.parse(f, logger=logger)
    assert len(mfile.types) == 2
    assert len(mfile.canonical_mentions) == 2
    assert len(mfile.links) == 2
    assert len(mfile.relations) == 0

def test_validate_tackb():
    logging.basicConfig(filename = '/tmp/tmp')

    testdir = os.path.join(os.path.dirname(__file__), "testdata")
    #logger = ListLogger()
    reader = TacKbReader()

    with gzip.open(os.path.join(testdir, "test_tac.kb.gz"), "rt") as f:
        mfile = reader.parse(f, logger=_logger)

    with gzip.open(os.path.join(testdir, "test_tac.kb.m.gz"), "wt") as f:
        mfile.write(f)

    assert len(mfile.types) == 2
    assert len(mfile.canonical_mentions) == 2
    assert len(mfile.links) == 2
    assert len(mfile.relations) == 0
