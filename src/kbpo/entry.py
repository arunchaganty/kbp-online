"""
Classes and functions to process entry files.
"""

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
        self._mention_map = {row.subj: row.obj for row in types}
        self._link_map = {row.subj: row.obj for row in links}
        self._cmention_map = {row.subj: row.obj for row in cmentions}
        return self

    def get_mention(self, m_id):
        return self._mention_map[m_id]
    def get_type(self, m_id):
        return self._type_map[m_id]
    def get_link(self, m_id):
        return self._link_map.get(self._cmention_map[m_id])

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
    def from_stream(cls, stream):
        """
        Split input into type, link, canonical_mention and relation definitions.
        """
        mentions = []
        links = []
        canonical_mentions = []
        relations = []

        for row in stream:
            assert len(row) <= 6, "Invalid number of columns, %d instead of %d"%(len(row), 6)
            row = row + [None] * (6-len(row))
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

class Entry(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'score', 'weight',])):
    @property
    def pair(self):
        return (self.subj, self.obj)

    @property
    def inv_pair(self):
        return (self.obj, self.subj)

def verify_mention_ids(mentions, canonical_mentions, links, relations):
    # Construct definitions of mentions.
    mention_ids = set(r[0] for r in mentions)
    assert len(mentions) == len(mention_ids), "Duplicate definitions of mentions"

    failed = False
    for r in canonical_mentions:
        subj, _, obj, _, _ = r
        if subj not in mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)
        if obj not in mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", obj, r)

    for r in links:
        subj, _, _, _, _ = r
        if subj not in mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)

    for r in relations:
        subj, _, obj, _, _ = r
        if subj not in mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)
        if obj not in mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", obj, r)
    assert not failed, "Couldn't find definitions of some mentions"

def verify_canonical_mentions(mentions, canonical_mentions, links, _):
    mention_ids = set(r[0] for r in mentions)

    failed = False
    # Construct definitions of mentions.
    links_ = {}
    for r in links:
        subj, _, obj, _, _ = r
        links_[subj] = obj

    canonical_mentions_ = {}
    for r in canonical_mentions:
        subj, _, obj, _, _ = r
        canonical_mentions_[subj] = obj
        links_[subj] = links_[obj]

    failed = False
    for m in mention_ids:
        if m not in canonical_mentions_:
            logger.error("Didn't have a canonical mention for %s", m)
            failed = True
        if m not in links_:
            logger.error("Didn't have a link for %s", m)
            failed = True
    assert not failed, "Couldn't find definitions of some mentions"

def verify_relations(mentions, canonical_mentions, links, relations):
    """
    symmetrize relations
    """
    # Map types.
    types = {r[0]: r[1] for r in mentions}

    relations_ = set()
    for r in relations:
        subj, reln, obj, prov, score = r

        if reln not in ALL_RELATIONS:
            logger.warning("Ignoring relation %s: %s", reln, r)
            continue
        reln = RELATION_MAP[reln]
        relations_.add((subj, reln, obj, prov, score))
    logger.info("Found %d relations", len(relations_))

    for r in relations:
        subj, reln, obj, prov, score = r

        if reln not in ALL_RELATIONS:
            continue

        if reln in INVERTED_RELATIONS:
            for reln_ in INVERTED_RELATIONS[reln]:
                if reln_.startswith(types[obj].lower()):
                    r_ = (obj, reln_, subj, prov, score)
                    if r_ not in relations_:
                        logger.warning("Adding symmetrized relation %s: %s", r_, r)
                        relations_.add(r_)
    logger.info("End with %d relations", len(relations_))
    return sorted(relations_)
