"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import sys
import csv
import logging
from enum import Enum
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

Message = namedtuple("Message", ["code", "short", "details"])
class Messages(Enum):
    """
    List of possible error messages
    """
    # Syntax errors
    INVALID_LINE = Message("E01", "Invalid number of columns", "found %(original)s instead of %(expected)s; ignoring line")
    INVALID_MENTION_PROVENANCE = Message("E02", "Invalid mention definition, missing provenance", "; ignoring definition")
    INVALID_RELATION_SELF = Message("E03","Invalid self-relation", "for %(subject_id)s %(reln) %(object_id); ignoring relation")
    INVALID_RELATION_ARGUMENTS = Message("E04", "Invalid relation arguments", "%(reln)s expects %(expected_arg1)s and %(expected_arg2)s, got %(actual_arg1)s and %(actual_arg2)s; ignoring relation")
    INVALID_PROVENANCE = Message("E05", "Provenance does not match string", "%(string)s is %(string_len)s characters, while provenance %(prov)s is %(prov_len)s characters; ")

    INVALID_CMENTION_PROVENANCE = Message("W06", "Canonical mention provenance outside mention document", "; ignoring canonical_mention")
    INVALID_RELATION_PROVENANCE = Message("W07", "Relation arguments or provenance come from different documents", "; ignoring relation")
    INVALID_LINK_RESERVED = Message("W08", "Using reserved linkname NILX[0-9]+", "Please use NIL[0-9]+ for NIL entities.; doing nothing")
    DUPLICATE_DEFINITION = Message("W09", "Duplicate definition", "; ignoring duplicate definition")

    # Inconsistent definitions
    INCONSISTENT_TYPE = Message("E11", "Inconsistent type", "for %(mention_id)s %(new)s,%(new)s conflicts with %(original)s; keeping %(original)s")
    INCONSISTENT_GLOSS = Message("E12", "Inconsistent gloss", "for %(mention_id)s %(new)s,%(new)s conflicts with %(original)s; keeping %(original)s")
    INCONSISTENT_CMENTION = Message("E13", "Inconsistent canonical_mention", "for %(mention_id)s %(new)s,%(new)s conflicts with %(original)s; keeping %(original)s")
    INCONSISTENT_LINK = Message("E14", "Inconsistent link", "for %(mention_id)s %(new)s, conflicts with %(original)s; keeping %(original)s")
    INCONSISTENT_ENTITY = Message("E11", "Inconsistent entity", "for %(mention_id)s, %(new)s conflicts with %(original)s; keeping %(original)s")
    INCONSISTENT_RELATION = Message("E15", "Inconsistent relation", "for %(subject_id)s and %(object_id)s, %(new)s conflicts with %(original)s; keeping %(original)s")
    INCONSISTENT_RELATION_SYMMETRIC = Message("E16","Inconsistent relation when symmetrized; %(new)s conflicts with %(original)s", "keeping %(original)s")

    # Missing definitions
    MISSING_ENTITY_TYPE = Message("E21", "Missing type", "for entity %(entity)s; ignoring entity")
    MISSING_PROVENANCE_DEFINITION=("E22", "Could not find definition for provenance", "for %(prov)s; ignoring definition")
    MISSING_PROVENANCE_RELATION = Message("W25", "Missing relation provanance", "; using between-mention span %(prov)s")
    MISSING_PROVENANCE_ARGUMENTS = Message("W26", "Missing subject/object provenance", "could not find provenance for %(entity)s in %(prov)s; ignoring relation")
    MISSING_PROVENANCE_CANONICAL = Message("W27", "Could not find canonical_mention in document", "for %(prov)s; using %(prov)s")
    MISSING_SYMMETRIC = Message("W28", "Missing symmetric relation", "for %(subject)s %(reln)s %(object)s; adding %(object)s %(inv_reln)s %(subject)s")
    MISSING_LINK = Message("W29", "Missing entity link", "for %(prov)s; using %(link)s")

    IGNORE_OUTOFCORPUS = Message("I31", "Mention outside corpus", "; ignoring definition")
    IGNORE_RELATION_UNSUPPORTED = Message("I32", "Relation not supported", "%(reln)s; ignoring definition")

class MessageAdapter(logging.LoggerAdapter):
    def log(self, lvl, msg, *args, **kwargs):
        if not isinstance(msg, Messages):
            return self.logger.log(lvl, msg, *args, **kwargs)

        # Override the lvl based on the code
        if msg.value.code.startswith("E"):
            lvl = logging.ERROR
        elif msg.value.code.startswith("W"):
            lvl = logging.WARNING
        else:
            lvl = logging.INFO

        if "lineno" in kwargs:
            line_desc = " (on line {})".format(kwargs["lineno"])
        else:
            line_desc=""

        msg = "[{code}] {short}, {details}{line_desc}".format(
            code=msg.value.code, 
            short=msg.value.short,
            details=msg.value.details % kwargs,
            line_desc=line_desc)
        self.logger.log(lvl, msg)

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
                self.logger.info(Messages.INCONSISTENT_TYPE, lineno=row.lineno, mention_id=row.subj, original=self._types[row.subj], new=row.reln)
            elif row.obj != self._glosses[row.subj]:
                self.logger.info(Messages.INCONSISTENT_GLOSS, lineno=row.lineno, mention_id=row.subj, original=self._glosses[row.subj], new=row.obj)
            else:
                self.logger.info(Messages.DUPLICATE_DEFINITION, lineno=row.lineno)
        else:
            self._types[row.subj] = row.reln
            self._glosses[row.subj] = row.obj

    def _add_cmention(self, row):
        assert row.reln == "canonical_mention"

        if row.subj in self._cmentions:
            if row.obj != self._cmentions[row.subj]:
                self.logger.info(Messages.INCONSISTENT_CMENTION, lineno=row.lineno, mention_id=row.subj, original=self._cmentions[row.subj], new=row.obj)
            else:
                self.logger.info(Messages.DUPLICATE_DEFINITION, lineno=row.lineno)
        else:
            self._cmentions[row.subj] = row.obj
            self._weights[row.subj, 'cmention'] = row.weight

    def _add_link(self, row):
        assert row.reln == "link"

        if row.subj in self._links and row.obj != self._links[row.subj]:
            self.logger.info(Messages.INCONSISTENT_LINK, lineno=row.lineno, mention_id=row.subj, original=self._links[row.subj], new=row.obj)
        else:
            if row.obj.startswith("NILX"):
                self.logger.info(Messages.INVALID_LINK_RESERVED, lineno=row.lineno)
            self._links[row.subj] = row.obj
            self._weights[row.subj, 'link'] = row.weight

    def _add_relation(self, row):
        assert row.reln in ALL_RELATIONS

        if (row.subj, row.obj) in self._relations and row.reln != self._relations[row.subj, row.obj]:
            self.logger.info(Messages.INCONSISTENT_RELATION, lineno=row.lineno, subject_id=row.subj, object_id=row.obj, original="{} {} {}".format(row.subj, self._relations[row.subj, row.obj], row.obj), new="{} {} {}".format(row.subj, row.reln, row.obj))
        else:
            if len(row.prov) == 0:
                row = row._replace(prov = (Provenance(row.subj.doc_id, min(row.subj.begin, row.obj.begin), max(row.subj.end, row.obj.end),)))
                self.logger.info(Messages.MISSING_PROVENANCE_RELATION, lineno=row.lineno, prov=row.prov)
            self._relations[row.subj, row.obj] = row.reln
            self._provenances[row.subj, row.obj] = row.prov
            self._weights[row.subj, row.obj] = row.weight

    def _check_doc_ids(self, row):
        doc_ids = self._doc_ids
        if doc_ids is not None and row.subj.doc_id not in doc_ids:
            self.logger.info(Messages.IGNORE_OUTOFCORPUS, lineno=row.lineno)
            return False
        elif row.reln == "canonical_mention" and row.subj.doc_id != row.obj.doc_id:
            self.logger.info(Messages.INVALID_CMENTION_PROVENANCE, lineno=row.lineno)
            return False
        elif row.reln in ALL_RELATIONS:
            if row.subj.doc_id != row.obj.doc_id:
                self.logger.info(Messages.INVALID_RELATION_PROVENANCE, lineno=row.lineno)
                return False
            elif any(row.subj.doc_id != p.doc_id for p in row.prov):
                self.logger.info(Messages.INVALID_RELATION_PROVENANCE, lineno=row.lineno)
                return False
        return True

    def _verify_mentions_defined(self):
        nil_count = 0
        for m in self._types:
            assert m in self._glosses
            if m not in self._cmentions:
                self.logger.info(Messages.MISSING_PROVENANCE_CANONICAL, prov=m)
                self._cmentions[m] = m
                self._weights[m, "cmention"] = 0.0
            if m not in self._links:
                link = "NILX{}".format(nil_count)
                self.logger.info(Messages.MISSING_LINK, prov=m, link=link)
                self._links[m] = link
                self._weights[m, "link"] = 0.0

        purge = set()
        for m, n in self._cmentions.items():
            if m not in self._types:
                self.logger.info(Messages.MISSING_PROVENANCE_DEFINITION, prov=m)
                purge.add(m)
            if n not in self._types:
                self.logger.info(Messages.MISSING_PROVENANCE_DEFINITION, prov=n)
                purge.add(m)
        for m in purge:
            del self._cmentions[m]
            del self._weights[m, 'cmention']

        purge = set()
        for m, n in self._links.items():
            if m not in self._types:
                self.logger.info(Messages.MISSING_PROVENANCE_DEFINITION, prov=m)
                purge.add(m)
        for m in purge:
            del self._links[m]
            del self._weights[m, 'link']

        purge = set()
        for (m, n), _ in self._relations.items():
            if m not in self._types:
                self.logger.info(Messages.MISSING_PROVENANCE_DEFINITION, prov=m)
                purge.add((m,n))
            if n not in self._types:
                self.logger.info(Messages.MISSING_PROVENANCE_DEFINITION, prov=n)
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
                self.logger.info(Messages.INVALID_RELATION_ARGUMENTS,
                         reln=r,
                         expected_arg1=subject_type, expected_arg2=object_types,
                         actual_arg1=self._types[m_], actual_arg2=self._types[n_],)
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
                            self.logger.info(Messages.INCONSISTENT_RELATION_SYMMETRIC,
                                     subject_id=m, object_id=n,
                                     new="{} {} {}".format(n, self._relations[n,m], m),
                                     original="{} {} {}".format(n, r_, m))
                        else:
                            self.logger.info(Messages.MISSING_SYMMETRIC, subject=m, reln=r, object=n, inv_reln=r_)

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

    def _namespace_links(self):
        for subj in self._links:
            if self._types[subj] == 'DATE':
                self._links[subj] = 'date:'+self._links[subj]


    def parse(self, fstream, doc_ids=None, logger=_logger, do_validate=True):
        """
        Parses (and validates) an m-file in the file stream @fstream.
        """
        reader = csv.reader(fstream, delimiter="\t")

        self.logger = MessageAdapter(logger, {})
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
                self.logger.info(Messages.INVALID_LINE, lineno=lineno, original=len(row), expected=5)
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
                self.logger.info(Messages.IGNORE_RELATION_UNSUPPORTED, lineno=row.lineno, reln=row.reln)


        if do_validate:
            self._validate()

        self._namespace_links()

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
            self.logger.info(Messages.INCONSISTENT_GLOSS, lineno=row.lineno, mention_id=row.prov, original=self._glosses[row.prov], new=row.obj)
        else:
            self._entity_mentions[row.subj, row.prov.doc_id].add(row.prov)
            self._glosses[row.prov] = row.obj

    def _add_entity_cmention(self, row):
        assert row.reln == "canonical_mention"

        if (row.subj, row.prov.doc_id) in self._entity_cmentions and self._entity_cmentions[row.subj, row.prov.doc_id] != row.prov:
            prov_ = self._entity_cmentions[row.subj, row.prov.doc_id]
            self.logger.info(Messages.INCONSISTENT_CMENTION, lineno=row.lineno, mention_id=row.subj, original=prov_, new=row.prov)
        else:
            self._entity_cmentions[row.subj, row.prov.doc_id] = row.prov
        self._add_entity_mention(row)

    def _add_entity_type(self, row):
        assert row.reln == "type"

        if row.subj in self._entity_types and self._entity_types[row.subj] != row.obj:
            self.logger.info(Messages.INCONSISTENT_TYPE, lineno=row.lineno, mention_id=row.subj, original=self._entity_types[row.subj,], new=row.obj)
        else:
            self._entity_types[row.subj] = row.obj

    def _add_entity_relation(self, row):
        assert row.reln in ALL_RELATIONS
        # Check if this is a self-relation. Complain.
        if row.subj == row.obj:
            self.logger.info(Messages.INVALID_RELATION_SELF, lineno=row.lineno, subject_id=row.subj, reln=row.reln, object_id=row.obj)
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
                    self.logger.info(Messages.INCONSISTENT_ENTITY, mention_id=mention, original=mention_map[mention], new=entity)
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
                self.logger.info(Messages.MISSING_ENTITY_TYPE, entity=entity)
                purge.add((entity, doc_id))
        for entity, doc_id in purge:
            for m in self._entity_mentions[entity, doc_id]:
                del self._glosses[m]
            del self._entity_mentions[entity, doc_id]

        purge = set()
        for entity, doc_id in self._entity_cmentions:
            if entity not in self._entity_types:
                self.logger.info(Messages.MISSING_ENTITY_TYPE, entity=entity)
                purge.add((entity, doc_id))
        for entity, doc_id in purge:
            del self._entity_cmentions[entity, doc_id]

        purge = set()
        for (subject, object_), rows in self._entity_relations.items():
            is_string_relation = any(row.reln in STRING_VALUED_RELATIONS for row in rows)
            if subject not in self._entity_types:
                self.logger.info(Messages.MISSING_ENTITY_TYPE, entity=entity)
                purge.add((subject, object_))
            if not is_string_relation and object_ not in self._entity_types:
                self.logger.info(Messages.MISSING_ENTITY_TYPE, entity=entity)
                purge.add((subject, object_))
        for entity, doc_id in purge:
            del self._entity_relations[subject, object_]

    def _verify_cmentions(self):
        # check that all mentions in a document have atleast one canonical mention.
        for entity, doc_id in self._entity_mentions:
            for m in self._entity_mentions[entity, doc_id]: # contains every mention.
                if (entity, m.doc_id) not in self._entity_cmentions:
                    self.logger.info(Messages.MISSING_PROVENANCE_CANONICAL, prov=m)
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
                self.logger.info(Messages.INVALID_PROVENANCE, string=object_gloss, string_len=len(object_gloss), prov=object_prov, prov_len= object_prov.end - object_prov.begin + 1)

            # TODO: Check for inconsistency here?
            self._add_mention(object_prov, gloss=object_gloss, type_=object_type, cmention=object_prov, link=object_gloss)

            for prov in row.prov[1:]:
                subject_prov = resolution_method(row.subj, prov)
                if subject_prov is not None: break
            else:
                self.logger.info(Messages.MISSING_PROVENANCE_ARGUMENTS, lineno=row.lineno, entity=row.subj, prov=prov)
                return False
        else:
            for prov in row.prov:
                subject_prov = resolution_method(row.subj, prov)
                if subject_prov is not None: break
            else:
                self.logger.info(Messages.MISSING_PROVENANCE_ARGUMENTS, lineno=row.lineno, entity=row.subj, prov=prov)
                return False

            for prov in row.prov:
                object_prov = resolution_method(row.obj, prov)
                if object_prov is not None: break
            else:
                self.logger.info(Messages.MISSING_PROVENANCE_ARGUMENTS, lineno=row.lineno, entity=row.obj, prov=prov)
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

        self.logger = MessageAdapter(logger, {})
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
                self.logger.info(Messages.INVALID_LINE, lineno=lineno, original=len(row), expected=5)
                continue

            row = row + [None] * (5-len(row)) + [lineno,]
            row = Entry(*row)
            row = row._replace(weight = float(row.weight) if row.weight else 0.0)
            if row.reln == 'mention':
                if row.prov is None:
                    self.logger.info(Messages.INVALID_MENTION_PROVENANCE, lineno=lineno)
                    continue
                row = row._replace(prov=Provenance.from_str(row.prov, inclusive=True))
                self._add_entity_mention(row)
            elif row.reln == 'canonical_mention':
                if row.prov is None:
                    self.logger.info(Messages.INVALID_MENTION_PROVENANCE, lineno=lineno)
                    continue
                row = row._replace(prov=Provenance.from_str(row.prov, inclusive=True))
                self._add_entity_cmention(row)
            elif row.reln == 'type':
                self._add_entity_type(row)
            elif row.reln in RELATION_MAP:
                row = row._replace(reln=RELATION_MAP[row.reln], prov=tuple(Provenance.from_str(p.strip(), inclusive=True) for p in row.prov.split(",")))
                self._add_entity_relation(row)
            else:
                self.logger.info(Messages.IGNORE_RELATION_UNSUPPORTED, lineno=lineno, reln=row.reln)

        if do_validate:
            self._validate()
        return self._build()

def test_validate_mfile():
    _logger.addHandler(logging.StreamHandler(sys.stderr))
    testdir = os.path.join(os.path.dirname(__file__), "testdata")
    reader = MFileReader()

    with gzip.open(os.path.join(testdir, "test_tac.m.gz"), "rt") as f:
        mfile = reader.parse(f)

    assert len(mfile.canonical_mentions) == len(mfile.types)
    assert len(mfile.links) == len(mfile.types)
    assert len(mfile.types) == 853860
    assert len(mfile.relations) == 66936

def test_validate_tackb():
    _logger.addHandler(logging.StreamHandler(sys.stderr))
    testdir = os.path.join(os.path.dirname(__file__), "testdata")
    reader = TacKbReader()

    with gzip.open(os.path.join(testdir, "test_tac.kb.gz"), "rt") as f:
        mfile = reader.parse(f)

    assert len(mfile.canonical_mentions) == len(mfile.types)
    assert len(mfile.links) == len(mfile.types)
    assert len(mfile.types) == 853860
    assert abs(len(mfile.relations) - 66936) < 100 # Eh, some nondeterminism.

    #reader_ = MFileReader()
    #with gzip.open(os.path.join(testdir, "test_tac.m.gz"), "rt") as f:
    #    mfile_ = reader_.parse(f)
    ## Uh oh, there are some tie breaking problems.
    ## assert mfile.types == mfile_.types
    ## assert mfile.links == mfile_.links
    ## assert mfile.canonical_mentions == mfile_.canonical_mentions
    ## assert mfile.relations == mfile_.relations

    with TemporaryFile() as f, gzip.open(f, "wt") as g:
        mfile.write(g)

if __name__ == '__main__':
    test_validate_mfile()
