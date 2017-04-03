"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import pdb
import re
import logging
from collections import namedtuple

from .defs import TYPES, RELATION_MAP, RELATIONS, ALL_RELATIONS, INVERTED_RELATIONS

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
        return re.match(r"([A-Za-z0-9]+):([0-9]+)-([0-9]+)", prov).groups()

    @classmethod
    def to_prov(cls, prov):
        assert len(prov) == 3
        return "{}:{}-{}".format(*prov)

    @classmethod
    def from_stream(cls, stream):
        """
        Split input into type, link, canonical_mention and relation definitions.
        """
        mentions = []
        links = []
        canonical_mentions = []
        relations = []

        for row in stream:
            assert len(row) <= 5, "Invalid number of columns, %d instead of %d"%(len(row), 5)
            row = row + [None] * (5-len(row))
            row = Entry(*row)

            if row.reln in TYPES:
                mentions.append(row)
            elif row.reln == "link":
                links.append(row)
            elif row.reln == "canonical_mention":
                canonical_mentions.append(row)
            else:
                relations.append(row)
        return cls(mentions, links, canonical_mentions, relations)

class Entry(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'weight',])):
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
    relations_ = set()
    for r in mfile.relations:
        subj, reln, obj = r.subj, r.reln, r.obj

        if reln not in ALL_RELATIONS:
            logger.warning("Ignoring relation %s: %s", reln, r)
            continue
        relations_.add(r._replace(reln=RELATION_MAP[reln]))
    logger.info("Found %d relations", len(relations_))

    for r in mfile.relations:
        subj, reln, obj = r.subj, r.reln, r.obj

        if reln not in ALL_RELATIONS:
            continue

        if reln in INVERTED_RELATIONS:
            for reln_ in INVERTED_RELATIONS[reln]:
                if reln_.startswith(mfile.get_type(obj).lower()):
                    r_ = r._replace(subj=obj, reln=reln_, obj=subj)
                    if r_ not in relations_:
                        logger.warning("Adding symmetrized relation %s: %s", r_, r)
                        relations_.add(r_)
    logger.info("End with %d relations", len(relations_))
    return mfile._replace(relations=relations_)
