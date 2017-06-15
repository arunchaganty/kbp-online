"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import pdb
import csv
import re
import logging
from collections import namedtuple, defaultdict

from .defs import TYPES, RELATION_MAP, RELATIONS, ALL_RELATIONS, INVERTED_RELATIONS, STRING_VALUED_RELATIONS
from .schema import Provenance
from . import db

import sys
from tqdm import tqdm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_MFile = namedtuple('_MFile', ['types', 'links', 'canonical_mentions', 'relations'])
class MFile(_MFile):
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
        subj, reln, obj = entry.subj, entry.reln, entry.obj
        if reln in RELATIONS:
            return entry
        elif reln not in RELATIONS and reln in INVERTED_RELATIONS:
            for reln_ in INVERTED_RELATIONS[reln]:
                if reln_.startswith(self.get_type(obj).lower()):
                    return entry._replace(subj = obj, reln = reln_, obj = subj)
        else:
            raise ValueError("Couldn't map relation for {}".format(entry))

    @classmethod
    def parse_prov(cls, prov):
        if len(prov) == 0:
            return None
        doc_id, beg, end =  re.match(r"([A-Za-z0-9_.]+):([0-9]+)-([0-9]+)", prov).groups()
        return Provenance(doc_id, int(beg), int(end))

    @classmethod
    def to_prov(cls, prov):
        assert len(prov) == 3
        return "{}:{}-{}".format(*prov)

    @classmethod
    def from_mfile_stream(cls, stream):
        mentions = []
        links = []
        canonical_mentions = []
        relations = []

        for row in stream:
            assert len(row) <= 5, "Invalid number of columns, %d instead of %d"%(len(row), 5)
            row = row + [None] * (5-len(row))
            row = Entry(*row)
            row = row._replace(
                subj = cls.parse_prov(row.subj),
                weight = float(row.weight) if row.weight else 0.0
                )

            if row.reln in TYPES:
                mentions.append(row)
            elif row.reln == "link":
                links.append(row)
            elif row.reln == "canonical_mention":
                row = row._replace(obj = cls.parse_prov(row.obj))
                canonical_mentions.append(row)
            else:
                provs = tuple(cls.parse_prov(p) for p in row.prov.split(',') if p)
                row = row._replace(obj = cls.parse_prov(row.obj), prov=provs)
                relations.append(row)
        return cls(mentions, links, canonical_mentions, relations)

    @classmethod
    def from_tac_stream(cls, stream):
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

        counter = 0
        raw_mentions = []
        raw_nominal_mentions = []
        raw_relations = []
        subj_2_type = UniqueDict()
        doc_id_subj_2_canonical_mention = UniqueDict()
        subj_doc_id_2_mention = defaultdict(list)
        for row in tqdm(stream):
            counter += 1
            if counter == 1:
                continue
            assert len(row) <= 5, "Invalid number of columns, %d instead of %d"%(len(row), 5)
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
                        m = first_contained_entity_prov(r_prov, row.subj)
                        if m is not None:
                            s_prov = m
                            break
                else:
                    for idx in range(len(split_prov)):
                        r_prov = cls.parse_prov(split_prov[idx])
                        s_prov = first_contained_entity_prov(r_prov, row.subj)
                        o_prov = first_contained_entity_prov(r_prov, row.obj)
                        if s_prov is not None and o_prov is not None:
                            break

                if s_prov is None or o_prov is None:
                    if s_prov is None:
                        logger.error("LINE %d: No mention found for subject %s in relation provenances %s", row.line_num, row.subj, row.prov)
                    if s_prov is None:
                        logger.error("LINE %d: No mention found for object %s in relation provenances %s", row.line_num, row.obj, row.prov)
                    #TODO: throw error
                else:
                    relations.append(Entry(s_prov, mapped_reln, o_prov, r_prov, row.weight))
        return cls(mentions, links, canonical_mentions, relations)

    @classmethod
    def from_stream(cls, stream, input_format='mfile'):
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
        if input_format == 'tac':
            return cls.from_tac_stream(stream)
        elif input_format == 'mfile':
            return cls.from_mfile_stream(stream)
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

class Entry(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'weight'])):
    @property
    def pair(self):
        return (self.subj, self.obj)

    @property
    def inv_pair(self):
        return (self.obj, self.subj)

def verify_mention_ids(mfile):
    # Construct definitions of mentions.
    if len(mfile.mention_ids) != len(mfile.types):
        logger.warning("%d Duplicate definitions of mentions", len(mfile.types) - len(mfile.mention_ids))
        seen_ids = set([])
        new_types = []
        for row in mfile.types:
            if row.subj not in seen_ids:
                seen_ids.add(row.subj)
                new_types.append(row)
        mfile = mfile._replace(types=new_types)

    failed = False
    for r in mfile.canonical_mentions:
        subj, _, obj, _, _ = r
        if subj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)
        if obj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", obj, r)

    for r in mfile.links:
        subj, _, _, _, _ = r
        if subj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)

    for r in mfile.relations:
        subj, _, obj, _, _ = r
        if subj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)
        if obj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", obj, r)
    assert not failed, "Couldn't find definitions of some mentions"
    return mfile

def verify_canonical_mentions(mfile):
    # Construct definitions of mentions.
    failed = False
    for m in mfile.mention_ids:
        if mfile.get_cmention(m) is None:
            logger.error("Didn't have a canonical mention for %s", m)
            failed = True
        if mfile.get_link(m) is None:
            logger.error("Didn't have a link for %s", m)
            pdb.set_trace()
            failed = True
    # TODO: link the first mention of this entity as the
    # canonical_mention
    assert not failed, "Couldn't find definitions of some mentions"
    return mfile

def verify_relations(mfile):
    """
    symmetrize relations
    """
    keys = set()
    relations_ = set()
    for r in mfile.relations:
        subj, reln, obj = r.subj, r.reln, r.obj

        if reln not in ALL_RELATIONS:
            logger.warning("Ignoring relation %s: %s", reln, r)
            continue
        if (subj, obj) in keys:
            logger.warning("Already have a relation between %s and %s", subj, obj)
            continue
        keys.add((subj, obj))
        relations_.add(r._replace(reln=RELATION_MAP[reln]))
    logger.info("Found %d relations", len(relations_))

    for r in mfile.relations:
        subj, reln, obj = r.subj, r.reln, r.obj

        if reln not in ALL_RELATIONS:
            continue

        # TODO: change consistent.
        if reln in INVERTED_RELATIONS:
            for reln_ in INVERTED_RELATIONS[reln]:
                if reln_.startswith(mfile.get_type(obj).lower()):
                    r_ = r._replace(subj=obj, reln=reln_, obj=subj)
                    if (obj, subj) not in keys: # Uh oh.
                        logger.info("Adding symmetrized relation %s: %s", r_, r)
                        keys.add((obj,subj))
                        relations_.add(r_)
    logger.info("End with %d relations", len(relations_))
    return mfile._replace(relations=relations_)

# TODO: make this validator 10x more robust
# TODO: have validator report errors (using a list).
def validate(fstream, input_format = 'mfile'):
    mfile = MFile.from_stream(csv.reader(fstream, delimiter='\t'), input_format)
    mfile = verify_mention_ids(mfile)
    mfile = verify_canonical_mentions(mfile)
    mfile = verify_relations(mfile)
    return mfile

def upload_submission(submission_id, mfile):
    with db.CONN:
        with db.CONN.cursor() as cur:
            # Create the submission
            mentions, links, relations = [], [], []
            for mention_id in mfile.mention_ids:
                mention_type, gloss, canonical_id = mfile.get_type(mention_id), mfile.get_gloss(mention_id), mfile.get_cmention(mention_id)
                mention_id, canonical_id = mention_id, canonical_id
                doc_id = mention_id.doc_id
                mentions.append((submission_id, doc_id, mention_id, canonical_id, mention_type, gloss))
            for row in mfile.links:
                mention_id = row.subj
                doc_id = mention_id.doc_id
                link_name = row.obj
                weight = row.weight
                links.append((submission_id, doc_id, mention_id, link_name, weight))
            for row in mfile.relations:
                subject_id = row.subj
                object_id = row.obj
                doc_id = subject_id.doc_id

                relation = row.reln
                provs = list(row.prov) if row.prov else []
                weight = row.weight
                relations.append((submission_id, doc_id, subject_id, object_id, relation, provs, weight))

            # mentions
            db.execute_values(cur, """INSERT INTO submission_mention (submission_id, doc_id, mention_id, canonical_id, mention_type, gloss) VALUES %s """, mentions)

            # links
            db.execute_values(cur, """INSERT INTO submission_link (submission_id, doc_id, mention_id, link_name, confidence) VALUES %s """, links)

            # relations
            db.execute_values(cur, """INSERT INTO submission_relation (submission_id, doc_id, subject_id, object_id, relation, provenances, confidence) VALUES %s """, relations)

# TODO: make into a test.
if __name__ == '__main__':
    logging.basicConfig(filename = '/tmp/tmp')
    #mfile = MFile.from_stream(csv.reader(sys.stdin, delimiter='\t'), input_format)
    validate(sys.stdin, input_format = 'tackb')
    #test_sanitize_mention_response()
