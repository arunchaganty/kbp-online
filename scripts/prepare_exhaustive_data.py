#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare data for exhaustive evaluation.
"""

import os
import random
import json
import sys
import logging
from collections import defaultdict

from util import ensure_dir, sample, query_docs, query_wikilinks, query_entities, query_dates, query_doc, query_mentions

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def remove_nested_mentions(mentions):
    ret = []
    for m in sorted(mentions, key=lambda m: (m["doc_char_end"] - m["doc_char_begin"], -m["doc_char_end"]), reverse=True):
        overlap = False
        for n in ret:
            if (m["doc_char_begin"] <= n["doc_char_begin"] <=  m["doc_char_end"]) or (m["doc_char_begin"] <= n["doc_char_end"] <= m["doc_char_end"]):
                #logger.warning("Ignoring %s b/c %s", m, n)
                overlap = True
                break
        if not overlap:
            ret.append(m)
    return sorted(ret, key=lambda m: m["doc_char_begin"])

def test_remove_nested_mentions():
    mentions = [{
        "id": 0,
        "doc_char_begin": 10,
        "doc_char_end": 20,
        },{
            "id": 1,
            "doc_char_begin": 15,
            "doc_char_end": 20,
        },{
            "id": 2,
            "doc_char_begin": 15,
            "doc_char_end": 25,
        },{
            "id": 3,
            "doc_char_begin": 25,
            "doc_char_end": 30,
        },{
            "id": 4,
            "doc_char_begin": 40,
            "doc_char_end": 50,
        }]

    mentions_ = remove_nested_mentions(mentions)
    assert [m["id"] for m in mentions_] == [0, 3, 4]

def link_to_wikipedia(doc_mentions):
    # Make freebase links to wikiones.
    fb_ids = sorted(set(m['entity']['link'] for ms in doc_mentions.values() for m in ms))
    logger.info("Mapping %d fb-ids to wikipedia", len(fb_ids))
    wikilink = dict(query_wikilinks(fb_ids))
    logger.info("Mapped %d fb-ids to wikipedia", len(wikilink))

    nil_count = 1
    for mentions in doc_mentions.values():
        for m in mentions:
            link = wikilink.get(m['entity']['link'])
            if link is None:
                # create a new NIL cluster
                link = "NIL{:04d}".format(nil_count)
                wikilink[m['entity']['link']] = link
            m['entity']['link'] = link
    logger.info("Used %d NIL ids", nil_count)

def collect_data(fstream, date_map):
    """
    Reads fstream and returns a stream of documents with mention annotations.
    """
    doc_mentions = defaultdict(list)
    ner_map = {
        "PER": "PER",
        "ORG": "ORG",
        "GPE": "GPE",
        "TTL": "TITLE",
        }

    for line in fstream:
        row = list(map(str.strip, line.strip().split("\t")))
        gloss, prov, link, ner, nom = row[2:7]
        doc_id, doc_span = prov.split(":")
        doc_char_begin, doc_char_end = doc_span.split("-")

        if nom == "NOM": continue
        if ner not in ner_map: continue
        ner = ner_map[ner]

        mention = {
            "gloss": gloss,
            "type":  ner,
            "doc_id": doc_id,
            "doc_char_begin": int(doc_char_begin) + 39, # Correcting a difference in offset format.
            "doc_char_end": int(doc_char_end) + 40,
            "entity": {
                "link": link
            }}
        doc_mentions[doc_id].append(mention)

    link_to_wikipedia(doc_mentions)

    for doc_id, mentions in doc_mentions.items():
        logger.warning("Getting data for doc-id %s (with %d mentions)", doc_id, len(mentions))
        mentions = remove_nested_mentions(mentions)

        yield {
            "doc_id": doc_id,
            "date": date_map.get(doc_id),
            "sentences": query_doc(doc_id),
            "suggested-mentions": query_mentions(doc_id),
            "mentions": mentions
            }

def make_date_map(fstream):
    ret = {}
    for line in fstream:
        doc_id, date = line.split("\t")
        ret[doc_id.strip()] = date.strip()
    return ret

def collect_sample(corpus_id, num_docs, per_entity, sentence_table, mention_table):
    # Sample 0.2 * n documents.
    docs = (d for d, in query_docs(corpus_id, sentence_table=sentence_table))

    doc_collection = set(sample(docs, int(.2 * num_docs)))
    logger.info("Seeding with %d documents", len(doc_collection))

    # Find all mentions and hence links in these documents.
    seed_entities = list(query_entities(sorted(doc_collection), mention_table=mention_table))
    logger.info("Found %d entities", len(seed_entities))
    random.shuffle(seed_entities)

    # Proceed to incrementally add documents to the collection using the
    # canonical glosses of entities.
    for entity_gloss, _ in seed_entities:
        logger.info("Searching for %s", entity_gloss)
        docs_ = set(d for d, in query_docs(corpus_id, [entity_gloss], sentence_table=sentence_table))
        docs_.difference_update(doc_collection)
        # Measure how many to sample.
        m = min(num_docs - len(doc_collection), per_entity)
        doc_collection.update(sample(docs_, m))
        logger.info("Now at %s", len(doc_collection))
        if len(doc_collection) >= num_docs: break
    assert len(doc_collection) == num_docs, "Couldn't find 'n' documents!"

    date_map = dict(query_dates(sorted(doc_collection)))

    for doc_id in doc_collection:
        yield {
            "doc_id": doc_id,
            "date": date_map[doc_id],
            "sentences": query_doc(doc_id,  sentence_table=sentence_table),
            "suggested-mentions": query_mentions(doc_id, mention_table=mention_table),
            }

def do_edl(args):
    date_map = make_date_map(args.dates)
    # Create output folder.
    ensure_dir(args.output)
    for doc in collect_data(args.input, date_map):
        with open(os.path.join(args.output, doc['doc_id'] + ".json"), 'w') as f:
            json.dump(doc, f)

def do_sample(args):
    random.seed(args.seed)
    ensure_dir(args.output)
    for doc in collect_sample(args.corpus, args.num_docs, args.per_entity, args.sentence_table, args.mention_table):
        with open(os.path.join(args.output, doc['doc_id'] + ".json"), 'w') as f:
            json.dump(doc, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Saves document to file in json format.')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('edl', help='' )
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default="data/english_edl.tab", help="Path to LDC2015E103 data")
    command_parser.add_argument('-d', '--dates', type=argparse.FileType('r'), default="data/english_edl.dates", help="Path to LDC2015E103 dates")
    command_parser.add_argument('-o', '--output', type=str, default="data/exhaustive/", help="A path to a folder to save documents.")
    command_parser.set_defaults(func=do_edl)

    command_parser = subparsers.add_parser('sample', help='Create an exhaustive dataset from the 2015 document corpus')
    command_parser.add_argument('-s', '--seed', type=int, default=42, help="Random seed to select documents.")
    command_parser.add_argument('-c', '--corpus', type=str, default="2016", help="Corpus to select documents from.")
    command_parser.add_argument('-n', '--num-docs', type=int, default=200, help="Number of documents to exhaustively sample")
    command_parser.add_argument('-p', '--per-entity', type=int, default=4, help="Number of documents to sample per entity")
    command_parser.add_argument('-mt', '--mention-table', type=str, default="mention_8_30_16", help="Mention table to use")
    command_parser.add_argument('-st', '--sentence-table', type=str, default="sentence_8_30_16", help="Sentence table")
    command_parser.add_argument('-o', '--output', type=str, default="data/exhaustive/", help="A path to a folder to save documents.")
    command_parser.set_defaults(func=do_sample)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
