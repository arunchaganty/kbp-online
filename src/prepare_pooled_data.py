#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare data for pooled evaluation.

Output format:
mention_id type gloss provenance _
mention_id canonical_mention mention_id_ _ confidence
mention_id link entity_id _ confidence
mention_id relation mention_id_ provenance confidence
"""

import os
import csv
import random
import json
import sys
import logging
from collections import defaultdict, Counter

from util import normalize, map_relations, make_list, query_psql, query_doc, query_mention_ids, query_mentions_by_id, ensure_dir, sample, ner_map, TYPES, ALL_RELATIONS, RELATIONS, INVERTED_RELATIONS, parse_input
from sample_util import sample_docs, sample_instances

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def is_reln(reln):
    return reln not in TYPES and reln != "canonical_mention" and reln != "link"

def as_prov(doc_id, begin, end):
    return "{}:{}-{}".format(doc_id, begin, end)

def parse_prov(prov):
    doc_id, begin_end = prov.split(":")
    begin, end = begin_end.split("-")
    return doc_id, int(begin), int(end)

def query_eval(writer, year=2015):
    """
    Grabs data from the kb_evaluation table.
    """

    # First, grab all the mentions in the eval.
    qry = """
SELECT subject_id FROM kb_evaluation e WHERE year={year}
UNION
SELECT object_id FROM kb_evaluation e WHERE year={year}
"""
    mention_ids = set(m for m, in query_psql(qry.format(year=year)))
    mention_ids = query_mention_ids(mention_ids)

    logger.info("Found %d mentions", len(mention_ids))

    for mention in query_mentions_by_id(mention_ids):
        id_, ner, gloss, doc_id, doc_char_begin, doc_char_end, link, canonical_id = mention
        if "_ENG_" not in doc_id: continue

        assert canonical_id in mention_ids, "couldn't find canonical mention {} for {}".format(canonical_id, id_)

        # a mention line
        if ner in ner_map:
            writer.writerow([id_, ner_map[ner], gloss, as_prov(doc_id, doc_char_begin, doc_char_end), None])
            # a canonical mention line
            writer.writerow([id_, "canonical_mention", canonical_id, "", 1.0])
            # a link line (only for canonical mentions
            if id_ == canonical_id:
                writer.writerow([id_, "link", link, "", 1.0])

    relations = query_psql("""
SELECT DISTINCT ON (subject_id, relation, object_id) subject_id, relation, object_id, s.doc_id, s.doc_char_begin[1], s.doc_char_end[array_length(s.doc_char_end)], is_correct
FROM kb_evaluation e, mention m, sentence s
WHERE year = {year}
  AND m.id = e.subject_id
  AND s.id = m.sentence_id
  AND s.doc_id = m.doc_id
ORDER BY subject_id, relation, object_id, doc_id, doc_char_begin
""".format(year=year, mention_ids=make_list(mention_ids)))
    for row in relations:
        subject_id, relation, object_id, doc_id, doc_char_begin, doc_char_end, is_correct = row
        if "_ENG_" not in doc_id or relation not in ALL_RELATIONS: continue
        if subject_id not in mention_ids or object_id not in mention_ids: continue

        writer.writerow([subject_id, relation, object_id, as_prov(doc_id, doc_char_begin, doc_char_end), 0.0 if is_correct == "W" else 1.0])

def query_submission(writer, kb_table, mention_table="mention", sentence_table="sentence"):
    """
    Grabs data from the kb_evaluation table.
    """
    # First, grab all the mentions in the eval.
    qry = """
SELECT subject_id FROM {kb} k
UNION
SELECT object_id FROM {kb} k
"""
    mention_ids = set(m for m, in query_psql(qry.format(kb=kb_table)))
    mention_ids = query_mention_ids(mention_ids, mention_table)
    logger.info("Found %d mentions", len(mention_ids))

    mention_ids_ = set()
    for mention in query_mentions_by_id(mention_ids, mention_table=mention_table):
        id_, ner, gloss, doc_id, doc_char_begin, doc_char_end, link, canonical_id = mention
        if "_ENG_" not in doc_id: continue
        assert canonical_id in mention_ids, "couldn't find canonical mention {} for {}".format(canonical_id, id_)
        # a mention line
        if ner in ner_map:
            mention_ids_.add(id_)
            writer.writerow([id_, ner_map[ner], gloss, as_prov(doc_id, doc_char_begin, doc_char_end), None])
            # a canonical mention line
            writer.writerow([id_, "canonical_mention", canonical_id, "", 1.0])
            # a link line (only for canonical mention
            if id_ == canonical_id:
                writer.writerow([id_, "link", link, "", 1.0])
    mention_ids = mention_ids_
    logger.info("Kept %d mentions", len(mention_ids))

    qry = """
SELECT DISTINCT ON (subject_id, relation, object_id) subject_id, relation, object_id, s.doc_id, s.doc_char_begin[1], s.doc_char_end[array_length(s.doc_char_end)], confidence
FROM {kb} e, {mention} m, {sentence} s
WHERE m.id = e.subject_id
  AND s.id = m.sentence_id
  AND s.doc_id = m.doc_id
ORDER BY subject_id, relation, object_id, doc_id, doc_char_begin
"""
    relations = query_psql(qry.format(kb=kb_table, mention=mention_table, sentence=sentence_table))
    for row in relations:
        subject_id, relation, object_id, doc_id, doc_char_begin, doc_char_end, confidence = row
        if "_ENG_" not in doc_id or relation not in ALL_RELATIONS: continue
        if subject_id not in mention_ids or object_id not in mention_ids: continue

        writer.writerow([subject_id, relation, object_id, as_prov(doc_id, doc_char_begin, doc_char_end), confidence])

def do_eval(args):
    writer = csv.writer(args.output, delimiter="\t")
    query_eval(writer, args.year)

def do_submission(args):
    writer = csv.writer(args.output, delimiter="\t")
    query_submission(writer, args.kb_table, args.mention_table, args.sentence_table)

def do_sample(args):
    """
    entity link -> [mentions]
    - sample entities
        - sample fills
            - sample mentions
    """
    random.seed(args.seed)

    # Read input
    reader = csv.reader(args.input, delimiter = "\t")
    mentions, canonical_mention, links, relations = parse_input(reader)
    entries = mentions + canonical_mention + links + relations
    old_entries = [parse_input(csv.reader(f, delimiter = "\t"))[-1] for f in args.old_entries]
    types = {r[0]: r[1] for r in mentions}

    if args.by_mention:
        relations = sample_by_mention(entries, args.num_entries)
    elif args.by_relation:
        relations = sample_by_relation(types, entries, args.num_entries, old_entries)
    else:
        relations = sample_by_entity(types, entries, args.num_entries, args.per_entity, old_entries)
    logger.info("Sampled %d relations", len(relations))

    relations = list(map_relations(mentions, relations))
    mentions = set(m for row in relations for m in [row[0], row[2]])
    mentions.update(row[2] for row in entries if row[1] == "canonical_mention" and row[0] in mentions)
    docs = set(parse_prov(row[3])[0] for row in relations)
    logger.info("Touches %d mentions + canonical-mentions from %d documents", len(mentions), len(docs))

    # Nones are for sampling weights.
    mentions = [row + [None, None, None] for row in entries if row[0] in mentions and not is_reln(row[1])]

    # Reconstruct output: collect all mentions, links, canonical mentions and relations.
    writer = csv.writer(args.output, delimiter="\t")
    for entry in mentions + relations:
        writer.writerow(entry)

def do_reweight(args):
    """
    entity link -> [mentions]
    - sample entities
        - sample fills
            - sample mentions
    """
    # Read input
    reader = csv.reader(args.reference, delimiter = "\t")
    mentions, canonical_mention, links, relations = parse_input(reader)
    entries = mentions + canonical_mention + links + relations
    types = {r[0]: r[1] for r in mentions}

    reader = csv.reader(args.input, delimiter = "\t")
    new_entries = sum(parse_input(reader), [])

    if args.by_relation:
        scheme = "relation"
    else:
        scheme = "entity"

    relations = reweight(types, entries, new_entries, scheme)
    # Don't need to do map because new_entries is ok
    mentions = set(m for row in relations for m in [row[0], row[2]])
    mentions.update(row[2] for row in entries if row[1] == "canonical_mention" and row[0] in mentions)
    docs = set(parse_prov(row[3])[0] for row in relations)
    logger.info("Touches %d mentions + canonical-mentions from %d documents", len(mentions), len(docs))
    # Nones are for sampling weights.
    mentions = [row + [None, None, None] for row in entries if row[0] in mentions and not is_reln(row[1])]

    # Reconstruct output: collect all mentions, links, canonical mentions and relations.
    writer = csv.writer(args.output, delimiter="\t")
    for entry in mentions + relations:
        writer.writerow(entry)

def do_make_task(args):
    """
    Build a table of documents and attach mentions and relations appropriately.
    """
    reader = csv.reader(args.input, delimiter = "\t")

    documents = defaultdict(lambda: {"mentions": {}, "relations":[]})
    mention_map = {}

    for row in reader: # Data is always cleaned.
        subj, relation, obj, prov, confidence, mention_weight, entity_weight, relation_weight = row

        if relation in TYPES: # new mention!
            assert subj not in mention_map, "Seeing a duplicate mention definition!?: {}".format(row)
            doc_id, begin, end = parse_prov(prov)

            mention_map[subj] = doc_id
            mentions = documents[doc_id]["mentions"]

            mentions[subj] = {
                "id": subj,
                "gloss": obj,
                "type": relation,
                "doc_char_begin": begin,
                "doc_char_end": end
                }

        elif relation == "canonical_mention":
            doc_id = mention_map[subj]
            mentions = documents[doc_id]["mentions"]

            if subj not in mentions or obj not in mentions:
                logger.warning("Couldn't find subject/object for canonical_mention: %s", row)
                continue
            other = mentions[obj]
            mentions[subj]["entity"] = {
                "id": other["id"],
                "gloss": other["gloss"],
                "link": other["link"],
                "doc_char_begin": other["doc_char_begin"],
                "doc_char_end": other["doc_char_end"],
                }

        elif relation == "link":
            doc_id = mention_map[subj]
            mentions = documents[doc_id]["mentions"]
            if subj not in mentions:
                logger.warning("Couldn't find subject for link: %s", row)
                continue
            mentions[subj]["link"] = obj

        else:
            doc_id, begin, end = parse_prov(prov)

            mentions = documents[doc_id]["mentions"]
            relations = documents[doc_id]["relations"]

            if subj not in mentions or obj not in mentions:
                logger.warning("Couldn't find subject/object for relation: %s", row)
                continue

            relations.append({
                "subject": mentions[subj],
                "relation": relation,
                "object": mentions[obj],
                "doc_char_begin": begin,
                "doc_char_end": end,
                "confidence": float(confidence),
                "mention_weight": float(mention_weight),
                "entity_weight": float(entity_weight),
                "relation_weight": float(relation_weight),
                })
    logger.info("Using %d documents", len(documents))

    ensure_dir(args.output)
    for doc_id, doc in documents.items():
        relations = doc['relations']
        doc['doc_id'] = doc_id
        doc['sentences'] = query_doc(doc_id, args.sentence_table)
        assert len(doc['sentences']) > 0, "Couldn't find document {}".format(doc_id)
        for relation in relations:
            doc['relations'] = [relation]
            b1, e1 = relation['subject']['doc_char_begin'], relation['subject']['doc_char_end']
            b2, e2 = relation['object']['doc_char_begin'], relation['object']['doc_char_end']

            logger.info("Saving %s with %d relations", doc_id, len(doc['relations']))
            with open(os.path.join(args.output, "{}-{}-{}-{}-{}.json".format(doc['doc_id'], b1, e1, b2, e2)), 'w') as f:
                json.dump(doc, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Saves document to file in json format.')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('eval', help='Grab labelled instances from evaluation data.')
    command_parser.add_argument('-y', '--year', type=str, default="2015", help="Year for which to get evaluations")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="data/pooled-eval.tsv", help="A path to a folder to save output.")
    command_parser.set_defaults(func=do_eval)

    command_parser = subparsers.add_parser('submission', help='Export mentions from database')
    command_parser.add_argument('-k', '--kb-table', type=str, default="kb_patterns_2016_8_28_16", help="KB table")
    command_parser.add_argument('-m', '--mention-table', type=str, default="mention_8_30_16", help="Mention table to use")
    command_parser.add_argument('-s', '--sentence-table', type=str, default="sentence_8_30_16", help="Sentence table")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="data/pooled-submission.tsv", help="A path to a folder to save output.")
    command_parser.set_defaults(func=do_submission)

    command_parser = subparsers.add_parser('sample', help='Sample entities')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default="data/pooled-eval.tsv", help="Input")
    command_parser.add_argument('-s', '--seed', type=int, default=42, help="Random seed")
    command_parser.add_argument('-n', '--num-entries', type=int, default=1000, help="Number of relation entries")
    command_parser.add_argument('-p', '--per-entity', type=int, default=10, help="Number of mentions to pick per entity")
    command_parser.add_argument('-m', '--by-mention', action='store_true', default=False, help="Sample entries by mentions instead of entities")
    command_parser.add_argument('-r', '--by-relation', action='store_true', default=False, help="Sample entries by relations instead of entities")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="data/pooled-eval-sample.tsv", help="A path to a folder to save output.")
    command_parser.add_argument('old_entries', type=argparse.FileType('r'), nargs="*", help="A path to a folder to save output.")
    command_parser.set_defaults(func=do_sample)

    command_parser = subparsers.add_parser('reweight', help='Sample entities')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), help="Input")
    command_parser.add_argument('-j', '--reference', type=argparse.FileType('r'), help="Original file that would be used to compute weights")
    command_parser.add_argument('-m', '--by-mention', action='store_true', default=False, help="Sample entries by mentions instead of entities")
    command_parser.add_argument('-r', '--by-relation', action='store_true', default=False, help="Sample entries by relations instead of entities")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="data/pooled-eval-sample.tsv", help="A path to a folder to save output.")
    command_parser.set_defaults(func=do_reweight)

    command_parser = subparsers.add_parser('make', help='Make output jsons from a submissions file')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), help="KB table")
    command_parser.add_argument('-m', '--mention-table', type=str, default="mention_8_30_16", help="Mention table to use")
    command_parser.add_argument('-s', '--sentence-table', type=str, default="sentence_8_30_16", help="Sentence table")
    command_parser.add_argument('-o', '--output', type=str, default="data/pooled-eval", help="A path to a folder to save output.")
    command_parser.set_defaults(func=do_make_task)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
