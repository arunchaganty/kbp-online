"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import csv
import logging
from collections import namedtuple, defaultdict

# For tests
import os
import gzip
from tempfile import TemporaryFile

from tqdm import tqdm

from .defs import TYPES, RELATION_MAP, RELATIONS, ALL_RELATIONS, INVERTED_RELATIONS, STRING_VALUED_RELATIONS, RELATION_TYPES
from .defs import get_inverted_relation
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
        self._doc_ids = None
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
                self.logger.warning("LINE %d: Inconsistent mention type: %s -> %s (keeping: %s)", row.lineno, row.subj, row.reln, self._types[row.subj])
            elif row.obj != self._glosses[row.subj]:
                self.logger.warning("LINE %d: Inconsistent mention gloss: %s -> %s (keeping: %s)", row.lineno, row.subj, row.obj, self._glosses[row.subj])
            else:
                self.logger.warning("LINE %d: Duplicate mention definition: %s", row.lineno, row)
        else:
            self._types[row.subj] = row.reln
            self._glosses[row.subj] = row.obj

    def _add_cmention(self, row):
        assert row.reln == "canonical_mention"

        if row.subj in self._cmentions:
            if row.obj != self._cmentions[row.subj]:
                self.logger.warning("LINE %d: Inconsistent canonical mention: %s -> %s (keeping: %s)", row.lineno, row.subj, row.obj, self._cmentions[row.subj])
            else:
                self.logger.warning("LINE %d: Duplicate canonical mention definition: %s", row.lineno, row)
        else:
            self._cmentions[row.subj] = row.obj
            self._weights[row.subj, 'cmention'] = row.weight

    def _add_link(self, row):
        assert row.reln == "link"

        if row.subj in self._links and row.obj != self._links[row.subj]:
            self.logger.warning("LINE %d: Inconsistent link: %s -> %s (keeping: %s)", row.lineno, row.subj, row.obj, self._links[row.subj])
        else:
            if row.obj.startswith("NILX"):
                self.logger.warning("LINE %d: Using reserved NILX linkspace: %s", row.lineno, row)
            self._links[row.subj] = row.obj
            self._weights[row.subj, 'link'] = row.weight

    def _add_relation(self, row):
        assert row.reln in ALL_RELATIONS

        if (row.subj, row.obj) in self._relations and row.reln != self._relations[row.subj, row.obj]:
            self.logger.warning("LINE %d: Inconsistent relation definition: (%s,%s) -> %s (keeping: %s)", row.lineno, row.subj, row.obj, row.reln, self._relations[row.subj, row.obj])
        else:
            if len(row.prov) == 0:
                self.logger.warning("LINE %d: Missing relation provenance, using between-mention span: %s", row.lineno, row)
                row = row._replace(prov = (Provenance(row.subj.doc_id, min(row.subj.begin, row.obj.begin), max(row.subj.end, row.obj.end),)))
            self._relations[row.subj, row.obj] = row.reln
            self._provenances[row.subj, row.obj] = row.prov
            self._weights[row.subj, row.obj] = row.weight

    def _check_doc_ids(self, row):
        doc_ids = self._doc_ids
        if doc_ids is not None and row.subj.doc_id not in doc_ids:
            self.logger.info("LINE %d: Ignoring mention outside corpus: %s", row.lineno, row)
            return False
        elif row.reln == "canonical_mention" and row.subj.doc_id != row.obj.doc_id:
            self.logger.warning("LINE %d: Canonical mention outside mention document: %s; ignoring mention", row.lineno, row)
            return False
        elif row.reln in ALL_RELATIONS:
            if row.subj.doc_id != row.obj.doc_id:
                self.logger.warning("LINE %d: object mention outside subject mention document: %s; ignoring relation", row.lineno, row)
                return False
            elif any(row.subj.doc_id != p.doc_id for p in row.prov):
                self.logger.warning("LINE %d: provenance outside mention document: %s; ignoring relation", row.lineno, row)
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
                self.logger.warning("LINE %d: Ignoring canonical_mention with missing mention: %s (in %s canonical_mention %s)", 0, m, m, n)
                purge.add(m)
            if n not in self._types:
                self.logger.warning("LINE %d: Ignoring canonical_mention with missing mention: %s (in %s canonical_mention %s)", 0, n, m, n)
                purge.add(m)
        for m in purge:
            del self._cmentions[m]
            del self._weights[m, 'cmention']

        purge = set()
        for m, n in self._links.items():
            if m not in self._types:
                self.logger.warning("LINE %d: Ignoring link with missing mention: %s (in %s link %s)", 0, m, m, n)
                purge.add(m)
        for m in purge:
            del self._links[m]
            del self._weights[m, 'link']

        purge = set()
        for (m, n), r in self._relations.items():
            if m not in self._types:
                self.logger.warning("LINE %d: Ignoring relation with missing mention: %s (in %s %s %s)", 0, m, m, r, n)
                purge.add((m,n))
            if n not in self._types:
                self.logger.warning("LINE %d: Ignoring relation with missing mention: %s (in %s %s %s)", 0, n, m, r, n)
                purge.add((m,n))
        for mn in purge:
            del self._relations[mn]
            del self._provenances[mn]
            del self._weights[mn]

    def _verify_relation_types(self):
        purge = set()
        for (m, n), r in self._relations.items():
            if r not in RELATIONS and r in INVERTED_RELATIONS:
                m_, r_, n_ = n, get_inverted_relation(r, self._types[n]), m
            else:
                m_, r_, n_ = m, r, n

            subject_type, object_types = RELATION_TYPES[r_] if r_ is not None else (None, [])
            if self._types[m_] != subject_type or self._types[n_] not in object_types:
                self.logger.warning("LINE %d: Ignoring relation with inconsistent argument types: %s(%s) %s %s(%s) (expected %s %s %s)",
                                    0, m, self._types[m], r, n, self._types[n],
                                    subject_type, '->' if r == r_ else '<-', object_types)
                purge.add((m,n))
        for mn in purge:
            del self._relations[mn]

    def _verify_symmetrized_relations(self):
        add, add_prov, add_weights = dict(), dict(), dict()
        for (m, n), r in self._relations.items():
            if (m, n) in add: continue # You'll be taken care of in due time.

            if r in INVERTED_RELATIONS:
                for r_ in INVERTED_RELATIONS[r]:
                    if r_.startswith(self._types[n].lower()):
                        assert (n, m) not in add # Not possible because (n, m) could only be in add if we had seen (m, n) before.
                        if (n, m) in self._relations and self._relations[n,m] == r_:
                            continue
                        elif (n, m) in self._relations and self._relations[n,m] != r_:
                            self.logger.warning("LINE %d: Ignoring inconsistent symmetric relation: %s %s %s when symmetrized conflicts with %s %s %s (removing latter)", 0, m, r, n, n, self._relations[n,m], m)
                        else:
                            self.logger.warning("LINE %d: Adding symmetrized relation: %s %s %s", 0, n, r_, m)

                        add[n,m] = r_
                        add_prov[n,m] = self._provenances[m,n]
                        add_weights[n,m] = self._weights[m,n]
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

    def parse(self, fstream, doc_ids=None, logger=_logger, do_validate=True):
        """
        Parses (and validates) an m-file in the file stream @fstream.
        """
        reader = csv.reader(fstream, delimiter="\t")

        self.logger = logger
        self._doc_ids = doc_ids
        self._types = dict()
        self._links = dict()
        self._glosses = dict()
        self._cmentions = dict()
        self._relations = dict()
        self._provenances = dict()
        self._weights = dict()

        # First pass of the data that builds the above tables.
        for lineno, row in enumerate(tqdm(reader, desc="reading file")):
            if len(row) == 0: continue # Skip empty lines
            if len(row) > 5:
                logger.error("LINE %d: Invalid number of columns: found %d instead of %d, %s", lineno, len(row), 5, row)
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
                logger.info("LINE %d: Ignoring relation %s: (not supported)", row.lineno, row.reln)
        if do_validate:
            self._validate()

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
            self.logger.warning("LINE %d: Ignoring inconsistent mention definition: %s (keeping %s %s)", row.lineno, row, row.prov, self._glosses[row.prov])
        else:
            self._entity_mentions[row.subj, row.prov.doc_id].add(row.prov)
            self._glosses[row.prov] = row.obj

    def _add_entity_cmention(self, row):
        assert row.reln == "canonical_mention"

        if (row.subj, row.prov.doc_id) in self._entity_cmentions and self._entity_cmentions[row.subj, row.prov.doc_id] != row.prov:
            prov_ = self._entity_cmentions[row.subj, row.prov.doc_id]
            self.logger.warning("LINE %d: Ignoring inconsistent canonical mention definition: %s (keeping %s %s)", row.lineno, row, prov_, self._glosses[prov_])
        else:
            self._entity_cmentions[row.subj, row.prov.doc_id] = row.prov
        self._add_entity_mention(row)

    def _add_entity_type(self, row):
        assert row.reln == "type"

        if row.subj in self._entity_types and self._entity_types[row.subj] != row.obj:
            self.logger.warning("LINE %d: Ignoring inconsistent type definition: %s (keeping %s)", row.lineno, row, self._entity_types[row.subj])
        else:
            self._entity_types[row.subj] = row.obj

    def _add_entity_relation(self, row):
        assert row.reln in ALL_RELATIONS
        # Check if this is a self-relation. Complain.
        if row.subj == row.obj:
            self.logger.warning("LINE %d: Ignoring invalid self-relation: %s", row.lineno, row)
        else:
            self._entity_relations[row.subj, row.obj].append(row)

    def _verify_unique_entity(self):
        """
        Check that there is a unique entity for every mention.
        """
        purge = set()
        mention_map = dict()
        for (entity, doc_id), mentions in self._entity_mentions.items():
            for mention in mentions:
                if mention in mention_map and mention_map[mention] != entity:
                    self.logger.warning("LINE %d: Mention refers to two entities: %s refers to %s and %s; keeping %s.",
                                      0, mention, entity, mention_map[mention], mention_map[mention])
                    purge.add((entity, doc_id, mention))
                mention_map[mention] = entity
        for entity, doc_id, mention in purge:
            self._entity_mentions[entity, doc_id].remove(mention)
            assert mention not in self._entity_mentions[entity, doc_id]

    def _verify_types(self):
        # check that all entities' types have been defined.
        purge = set()
        for entity, doc_id in self._entity_mentions:
            if entity not in self._entity_types:
                self.logger.warning("LINE %d: Type not found for entity: ignoring %s", 0, entity)
                purge.add((entity, doc_id))
        for entity, doc_id in purge:
            for m in self._entity_mentions[entity, doc_id]:
                del self._glosses[m]
            del self._entity_mentions[entity, doc_id]

        purge = set()
        for entity, doc_id in self._entity_cmentions:
            if entity not in self._entity_types:
                self.logger.warning("LINE %d: Type not found for entity: ignoring %s", 0, entity)
                purge.add((entity, doc_id))
        for entity, doc_id in purge:
            del self._entity_cmentions[entity, doc_id]

        purge = set()
        for (subject, object_), rows in self._entity_relations.items():
            is_string_relation = any(row.reln in STRING_VALUED_RELATIONS for row in rows)
            if subject not in self._entity_types:
                self.logger.warning("LINE %d: Type not found for entity: ignoring %s", 0, entity)
                purge.add((subject, object_))
            if not is_string_relation and object_ not in self._entity_types:
                self.logger.warning("LINE %d: Type not found for entity: ignoring %s", 0, entity)
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
        for m in sorted(self._entity_mentions[entity, prov.doc_id]):
            if m.begin >= prov.begin and m.end <= prov.end:
                return m

    def _find_first_overlapping_mention(self, entity, prov):
        for m in sorted(self._entity_mentions[entity, prov.doc_id]):
            if (m.begin >= prov.begin and m.begin <= prov.end) or \
                    (m.end >= prov.begin and m.end <= prov.end):
                return m

    def _find_first_subsequent_mention(self, entity, prov):
        for m in sorted(self._entity_mentions[entity, prov.doc_id]):
            if m.begin >= prov.begin:
                return m

    def _add_mention(self, prov, gloss, type_, cmention, link, lineno=0):
        assert prov not in self._types or self._types[prov] == type_
        assert prov not in self._glosses or self._glosses[prov] == gloss
        assert prov not in self._cmentions or self._cmentions[prov] == cmention
        assert prov not in self._links or self._links[prov] == link

        self._types[prov] = type_
        self._glosses[prov] = gloss
        self._cmentions[prov] = cmention
        self._weights[prov, 'cmention'] = 0.0
        self._links[prov] = link
        self._weights[prov, 'link'] = 0.0

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
            # Note, that dates get canonicalized and so we don't do
            # provenance string checking there.
            if object_type != "DATE" and (object_prov.end - object_prov.begin + 1) != len(object_gloss):
                self.logger.warning("LINE %d: Provenance does not match string: %s (%d characters) maps to %s (%d characters)",
                                    0, object_prov, object_prov.end - object_prov.begin + 1, object_gloss, len(object_gloss))

            # TODO: Check for inconsistency here?
            self._add_mention(object_prov, gloss=object_gloss, type_=object_type, cmention=object_prov, link=object_gloss)

            for prov in row.prov[1:]:
                subject_prov = resolution_method(row.subj, prov)
                if subject_prov is not None: break
            else:
                self.logger.warning("LINE %d: Could not find provenance for subject: ignoring %s", row.lineno, row)
                return False
        else:
            for prov in row.prov:
                subject_prov = resolution_method(row.subj, prov)
                if subject_prov is not None: break
            else:
                self.logger.warning("LINE %d: Could not find provenance for subject: ignoring %s", row.lineno, row)
                return False

            for prov in row.prov:
                object_prov = resolution_method(row.obj, prov)
                if object_prov is not None: break
            else:
                self.logger.warning("LINE %d: Could not find provenance for object: ignoring %s", row.lineno, row)
                return False

        # TODO check consistency (only 1 relation) 
        self._relations[subject_prov, object_prov] = row.reln
        self._provenances[subject_prov, object_prov] = row.prov
        self._weights[subject_prov, object_prov] = row.weight

        return True

    def _resolve_relations(self, resolution_method=None):
        if resolution_method is None:
            resolution_method = self._find_first_subsequent_mention

        for relations in tqdm(self._entity_relations.values(), desc="resolving entity relations"):
            for row in relations:
                self._resolve_arguments(row)

    def _validate(self):
        self._verify_unique_entity()
        self._verify_types()
        self._verify_cmentions()
        self._resolve_relations()

    def _build(self, do_validate=True):
        # Add mentions
        for (entity, _), mentions in self._entity_mentions.items():
            entity_type = self._entity_types[entity]
            for m in mentions:
                self._add_mention(m, gloss=self._glosses[m], type_=entity_type, cmention=self._entity_cmentions[entity, m.doc_id], link=entity)

        if do_validate:
            MFileReader._validate(self)
        return MFileReader._build(self)

    def parse(self, fstream, doc_ids=None, logger=_logger, do_validate=True):
        reader = csv.reader(fstream, delimiter="\t")

        self.logger = logger
        # intermediate stuff.
        self._entity_mentions = defaultdict(set)
        self._entity_cmentions = dict()
        self._entity_types = dict()
        self._entity_relations = defaultdict(list)

        # Used in final output
        self._doc_ids = doc_ids
        self._types = dict()
        self._glosses = dict()
        self._cmentions = dict()
        self._links = dict()
        self._relations = dict()
        self._provenances = dict()
        self._weights = dict()

        # First pass of the data that builds the above tables.
        for lineno, row in enumerate(tqdm(reader, desc="reading file")):
            if lineno == 0: continue # skip system header
            if len(row) == 0: continue # skip empty lines

            if len(row) > 5:
                self.logger.error("LINE %d: Invalid number of columns: found %d instead of %d, %s", lineno, len(row), 5, row)
                continue

            row = row + [None] * (5-len(row)) + [lineno,]
            row = Entry(*row)
            row = row._replace(weight = float(row.weight) if row.weight else 0.0)
            if row.reln == 'mention':
                if row.prov is None:
                    self.logger.warning("LINE %d: Ignoring mention without provenance: %s", row.lineno, row)
                    continue
                row = row._replace(prov=Provenance.from_str(row.prov))
                self._add_entity_mention(row)
            elif row.reln == 'canonical_mention':
                if row.prov is None:
                    self.logger.warning("LINE %d: Ignoring mention without provenance: %s", row.lineno, row)
                    continue
                row = row._replace(prov=Provenance.from_str(row.prov))
                self._add_entity_cmention(row)
            elif row.reln == 'type':
                self._add_entity_type(row)
            elif row.reln in RELATION_MAP:
                row = row._replace(reln=RELATION_MAP[row.reln], prov=tuple(Provenance.from_str(p.strip()) for p in row.prov.split(",")))
                self._add_entity_relation(row)
            else:
                self.logger.info("LINE %d: Ignoring relation: %s (not supported)", row.lineno, row.reln)

        if do_validate:
            self._validate()
        return self._build()

def test_validate_mfile():
    testdir = os.path.join(os.path.dirname(__file__), "testdata")
    logger = ListLogger()
    reader = MFileReader()

    with gzip.open(os.path.join(testdir, "test_tac.m.gz"), "rt") as f:
        mfile = reader.parse(f, logger=logger)

    assert len(logger.errors) == 0
    assert len(logger.warnings) == 0
    assert len(mfile.canonical_mentions) == len(mfile.types)
    assert len(mfile.links) == len(mfile.types)
    assert len(mfile.types) == 853860
    assert len(mfile.relations) == 66936

def test_validate_tackb():
    logger = ListLogger()
    testdir = os.path.join(os.path.dirname(__file__), "testdata")
    reader = TacKbReader()

    with gzip.open(os.path.join(testdir, "test_tac.kb.gz"), "rt") as f:
        mfile = reader.parse(f, logger=logger)

    assert len(logger.errors) == 0
    assert len(mfile.canonical_mentions) == len(mfile.types)
    assert len(mfile.links) == len(mfile.types)
    assert len(mfile.types) == 853860
    assert abs(len(mfile.relations) - 66936) < 100 # Eh, some nondeterminism.

    reader_ = MFileReader()
    with gzip.open(os.path.join(testdir, "test_tac.m.gz"), "rt") as f:
        mfile_ = reader_.parse(f, logger=logger)
    assert mfile.types == mfile_.types
    assert mfile.links == mfile_.links
    assert mfile.canonical_mentions == mfile_.canonical_mentions
    assert mfile.relations == mfile_.relations

    with TemporaryFile() as f, gzip.open(os.path.join(testdir, f), "wt") as g:
        mfile.write(g)
