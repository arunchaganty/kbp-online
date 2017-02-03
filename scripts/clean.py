#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performs sanity checks on mentions data.
"""

import csv
import sys
import logging

from util import TYPES, RELATION_MAP, RELATIONS, ALL_RELATIONS, INVERTED_RELATIONS, parse_input

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def do_command(args):
    reader = csv.reader(args.input, delimiter='\t')
    mentions, links, canonical_mentions, relations = parse_input(reader)

    # Verify that canonical mentions are correctly linked.
    verify_mention_ids(mentions, canonical_mentions, links, relations)
    verify_canonical_mentions(mentions, canonical_mentions, links, relations)
    relations = verify_relations(mentions, canonical_mentions, links, relations)

    entries = mentions + links + canonical_mentions + relations
    writer = csv.writer(args.output, delimiter='\t')
    for row in entries:
        writer.writerow(row)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Performs sanity checks and corrects simple mistakes')
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)
