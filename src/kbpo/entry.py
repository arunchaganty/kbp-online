"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import pdb

import os
import re
import sys
import csv
import logging
from collections import namedtuple, defaultdict

from tqdm import tqdm

from .defs import TYPES, RELATION_MAP, ALL_RELATIONS, INVERTED_RELATIONS, STRING_VALUED_RELATIONS, standardize_relation
from .schema import Provenance

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

def parse_prov(prov):
    if len(prov) == 0:
        return None
    doc_id, beg, end =  re.match(r"([A-Za-z0-9_.]+):([0-9]+)-([0-9]+)", prov).groups()
    return Provenance(doc_id, int(beg), int(end))

def to_prov(prov):
    assert len(prov) == 3, "Invalid provenance format: {}".format(prov)
    return "{}:{}-{}".format(*prov)

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

    @classmethod
    def parse_prov(cls, prov):
        if len(prov) == 0:
            return None
        doc_id, beg, end =  re.match(r"([A-Za-z0-9_.]+):([0-9]+)-([0-9]+)", prov).groups()
        return Provenance(doc_id, int(beg), int(end))

    @classmethod
    def to_prov(cls, prov):
        assert len(prov) == 3, "Invalid provenance format: {}".format(prov)
        return "{}:{}-{}".format(*prov)

    @classmethod
    def from_tac_stream(cls, stream, logger = _logger):
        mentions = []
        links = []
        canonical_mentions = []
        relations = []

        class EntryLine(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'weight', 'line_num'])):
            @property
            def pair(self):
                return (self.subj, self.obj)

            @property
            def inv_pair(self):
                return (self.obj, self.subj)

        class UniqueDict(dict):
            def __setitem__(self, key, value):
                if key not in self:
                    dict.__setitem__(self, key, value)
                else:
                    raise KeyError("Key already exists")

        raw_mentions = []
        raw_nominal_mentions = []
        raw_relations = []
        subj_2_type = UniqueDict()
        doc_id_subj_2_canonical_mention = UniqueDict()
        subj_doc_id_2_mention = defaultdict(list)
        for counter, row in enumerate(tqdm(stream)):
            if counter == 0: continue
            if row == '': continue

            if len(row) > 5:
                logger.error("LINE %d: Invalid number of columns, %d instead of %d", counter, len(row), 5)
                continue

            row = row + [None] * (5-len(row)) + [counter]
            reln = row[1]
            if reln == 'mention':
                if row[3] is None:
                    logger.error("LINE %d: No provenance for mention", counter)
                    continue
                row[3] = cls.parse_prov(row[3])
                row = EntryLine(*row)
                raw_mentions.append(row)
                subj_doc_id_2_mention[(row.subj, row.prov.doc_id)].append(row)
            elif reln == 'canonical_mention':
                #raw_canonical_mentions.append(row)
                if row[3] is None:
                    logger.error("LINE %d: No provenance for mention", counter)
                    continue
                row[3] = cls.parse_prov(row[3])
                row = EntryLine(*row)
                try:
                    doc_id_subj_2_canonical_mention[(row.prov.doc_id, row.subj)] = row
                except KeyError:
                    logger.warning("LINE %d: Duplicate canonical mention of entity %s, in document %d", counter, row.subj, row.prov.doc_id)
                    continue
                raw_mentions.append(row)

            elif reln == 'nominal_mention':
                row = EntryLine(*row)
                raw_nominal_mentions.append(row)

            elif reln == 'type':
                #raw_types.append(row)
                row = EntryLine(*row)
                try:
                    subj_2_type[row.subj] = row
                except KeyError:
                    if subj_2_type[row.subj].obj == row.obj:
                        logger.warning("LINE %d: Duplicate type for entity %s", counter, row.subj)
                        continue
                    else:
                        logger.error("LINE %d: Inconsistent types (with line %d) for entity %s", counter,subj_2_type[row.subj].line_num, row.subj)
                        continue


            else:
                row = EntryLine(*row)
                raw_relations.append(row)

        #types
        for row in tqdm(raw_mentions):
            if row.subj not in subj_2_type:
                logger.error("LINE %d: Type not found for mention %s", row.line_num, row.subj)
            type_row = subj_2_type[row.subj]
            mentions.append(Entry(row.prov, type_row.obj, row.obj, None, row.weight))

        #canonical-mentions
        for row in tqdm(raw_mentions):
            if (row.prov.doc_id, row.subj) not in doc_id_subj_2_canonical_mention:
                logger.error("LINE %d: Canonical mention not found for entity %s in document %d", row.line_num, row.subj, row.prov.doc_id)
            canonical_row = doc_id_subj_2_canonical_mention[(row.prov.doc_id, row.subj)]
            canonical_mentions.append(Entry(row.prov, 'canonical_mention', canonical_row.prov, None, canonical_row.weight))

        #entity_links
        for row in tqdm(raw_mentions):
            links.append(Entry(row.prov, 'link', row.subj, None, row.weight))

        def first_contained_entity_prov(reln_prov, entity):
            for m in subj_doc_id_2_mention[(entity, reln_prov.doc_id)]:
                if m.prov.begin >= reln_prov.begin and m.prov.end <= reln_prov.end:
                    return m.prov

        def first_overlapping_entity_prov(reln_prov, entity):
            for m in subj_doc_id_2_mention[(entity, reln_prov.doc_id)]:
                if (m.prov.begin >= reln_prov.begin and m.prov.begin <= reln_prov.end) or (m.prov.end >= reln_prov.begin and m.prov.end <= reln_prov.end):
                    return m.prov

        def first_entity_prov(reln_prov, entity):
            for m in subj_doc_id_2_mention[(entity, reln_prov.doc_id)]:
                #if m.prov.begin >= reln_prov.begin and m.prov.begin <= reln_prov.begin+2000:
                if m.prov.begin >= reln_prov.begin:
                    return m.prov

        ##relations
        all_relations = set(RELATION_MAP.keys()) - set(['no_relation'])
        ignored_relations = set(['per:alternate_names', 'org:alternate_names'])
        all_relations -= ignored_relations
        for row in tqdm(raw_relations):
            if row.reln not in all_relations:
                if row.reln in ignored_relations:
                    logger.warning("LINE %d: Ignored relation %s", row.line_num, row.reln)
                else:
                    logger.warning("LINE %d: Unsupported relation %s", row.line_num, row.reln)
            else:
                mapped_reln = RELATION_MAP[row.reln]
                split_prov = row.prov.split(',')
                if len(split_prov) == 0:
                    logger.error("LINE %d: No provenance for relation", row.line_num)
                    continue

                s_prov = None
                o_prov = None
                r_prov = None
                if mapped_reln in STRING_VALUED_RELATIONS:
                    # First provenance would give object provenance
                    o_prov = cls.parse_prov(split_prov[0])
                    #TODO: make sure gloss is the same as the first provenance
                    mentions.append(Entry(o_prov, STRING_VALUED_RELATIONS[mapped_reln], row.obj, None, row.weight))
                    canonical_mentions.append(Entry(o_prov, 'canonical_mention', o_prov, None, row.weight))
                    links.append(Entry(o_prov, 'link', row.obj, None, row.weight))
                    for idx in range(1,len(split_prov)):
                        r_prov = cls.parse_prov(split_prov[idx])
                        m = first_entity_prov(r_prov, row.subj)
                        if m is not None:
                            s_prov = m
                            break
                else:
                    for idx in range(len(split_prov)):
                        r_prov = cls.parse_prov(split_prov[idx])
                        s_prov = first_entity_prov(r_prov, row.subj)
                        o_prov = first_entity_prov(r_prov, row.obj)
                        if s_prov is not None and o_prov is not None:
                            break

                if s_prov is None or o_prov is None:
                    if s_prov is None:
                        logger.error("LINE %d: No mention found for subject %s in relation provenances %s", row.line_num, row.subj, row.prov)
                    if o_prov is None:
                        logger.error("LINE %d: No mention found for object %s in relation provenances %s", row.line_num, row.obj, row.prov)
                else:
                    relations.append(Entry(s_prov, mapped_reln, o_prov, tuple(cls.parse_prov(x) for x in split_prov), row.weight))
        for mn in purge:
            del self._relations[mn]
        return cls(mentions, links, canonical_mentions, relations)

    @classmethod
    def from_stream(cls, stream, input_format='mfile', logger = _logger):
        """
        Split input into type, link, canonical_mention and relation definitions.
        @input_format can be mfile or tackb
            tackb input format is
                :<e1> type <type>
                :<e1> mention <string> <provenance>
                :<e1> canonical_mention <string> <provenance>
                :<e1> nominal_mention <string> <provenance> (ignored)
                :<e1> <predicate> :<e2> <provenance> <weight>
                :<e1> <predicate> <string> <provenance> <weight>
            mfile input format is
                <m1:prov> <predicate> <m2:prov> <rel:prov> weight
                <m1:prov> <type> <gloss> weight
                <m1:prov> canonical_mention <m2:prov> weight
                <m1:prov> link <wiki-link> weight
        """
        if input_format == 'tackb':
            return cls.from_tac_stream(stream, logger)
        elif input_format == 'mfile':
            return cls.from_mfile_stream(stream, logger)
        else:
            raise ValueError("Invalid file format, should be tackb or mfile")

    def to_stream(self, stream):
        for row in self.types:
            stream.writerow([MFile.to_prov(row.subj), row.reln, row.obj, row.prov, row.weight])
        for row in self.links:
            stream.writerow([MFile.to_prov(row.subj), row.reln, row.obj, row.prov, row.weight])
        for row in self.canonical_mentions:
            stream.writerow([MFile.to_prov(row.subj), row.reln, MFile.to_prov(row.obj), row.prov, row.weight])
        for row in self.relations:
            stream.writerow([MFile.to_prov(row.subj), row.reln, MFile.to_prov(row.obj), ",".join([MFile.to_prov(p) for p in row.prov]), row.weight])

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
                self.logger.error("LINE %d: Inconsistent relation argument types: %s(%s) %s %s(%s) (execpted %s -> %s)", 0, m, self._types[m], r, n, self._types[n], n, *RELATION_MAP[r])
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
        for lineno, row in enumerate(reader):
            if len(row) == 0: continue # Skip empty lines
            if len(row) > 5:
                logger.error("LINE %d: Invalid number of columns, %d instead of %d", lineno, len(row), 5)
                continue
            row = row + [None] * (5-len(row)) + [lineno,]
            row = Entry(*row)
            row = row._replace(subj = parse_prov(row.subj), weight = float(row.weight) if row.weight else 0.0)

            if row.reln in TYPES:
                if self._check_doc_ids(row):
                    self._add_mention(row)
            elif row.reln == "link":
                if self._check_doc_ids(row):
                    self._add_link(row)
            elif row.reln == "canonical_mention":
                row = row._replace(obj = parse_prov(row.obj))
                if self._check_doc_ids(row):
                    self._add_cmention(row)
            elif row.reln in ALL_RELATIONS:
                provs = tuple(parse_prov(p.strip()) for p in row.prov.split(',') if p)
                row = row._replace( reln=RELATION_MAP[row.reln], obj = parse_prov(row.obj), prov=provs)
                if self._check_doc_ids(row):
                    self._add_relation(row)
            else:
                logger.warning("LINE %d: Ignoring relation: %s (not supported)", row.lineno, row.reln)
        
        self._verify_mentions_defined()
        self._verify_relation_types()
        self._verify_symmetrized_relations()

        return self._build()

# TODO: make this validator 10x more robust
# TODO: have validator report errors (using a list).
def validate(fstream, input_format = 'mfile', logger=_logger, doc_ids=None):
    mfile = MFile.from_stream(csv.reader(fstream, delimiter='\t'), input_format, logger)
    if doc_ids:
        mfile = verify_doc_ids(mfile, doc_ids, logger)
    mfile = verify_mention_ids(mfile, logger)
    mfile = verify_canonical_mentions(mfile, logger)
    mfile = verify_relations(mfile, logger)
    return mfile

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
    pass

# TODO: make into a test.
if __name__ == '__main__':
    logging.basicConfig(filename = '/tmp/tmp')
    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.DEBUG)
    #mfile = MFile.from_stream(csv.reader(sys.stdin, delimiter='\t'), input_format)
    validate(sys.stdin, input_format = 'tackb', logger=_logger)
    #test_sanitize_mention_response()
