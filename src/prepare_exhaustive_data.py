#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare data for exhaustive evaluation.
"""

import os
import csv
import random
import json
import sys
import logging
from collections import defaultdict, Counter

import psycopg2
import numpy as np

from util import ensure_dir, sample, query_docs, query_wikilinks, query_entities, query_dates, query_doc, query_mentions, raw_psql, query_psql, sanitize

logging.basicConfig(level=logging.INFO)
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
                nil_count += 1
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
    doc_collection = sample_docs_entity(corpus_id, num_docs, per_entity, sentence_table, mention_table)

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

def compute_entropy(entity_list, frequencies):
    """
    Compute entropy of the entity list.
    """
    total = sum(frequencies.values())

    ret, cnt = 0., 0.
    for entity, _ in entity_list:
        # Ignore these.
        if entity not in frequencies: continue
        cnt += 1
        ret += (np.log(frequencies[entity]) - ret)/cnt
    return np.log(total) - ret # normalizing.

def get_binned_frequencies(entity_list, frequencies, n_bins=3):
    max_freq = np.log(max(frequencies.values()))
    logger.info("Using bin size: {0:.3f}".format(max_freq/n_bins))

    counts = [0] * n_bins
    for entity, count in entity_list:
        if entity not in frequencies: continue
        bin_idx = min(int(np.floor(np.log(frequencies[entity])/max_freq * n_bins)), n_bins-1)
        counts[bin_idx] += 1

    # Normalize into frequencies.
    return counts

def compute_stats(entity_list, mention_freqs, doc_freqs):
    entropy = compute_entropy(entity_list, mention_freqs)
    mention_counts = get_binned_frequencies(entity_list, mention_freqs)
    doc_counts = get_binned_frequencies(entity_list, doc_freqs)

    return entropy, mention_counts, doc_counts

def get_document_links(docs, entities):
    conn = psycopg2.connect("dbname=kbp user=kbp host=localhost port=4242")
    cur = conn.cursor()
    cur.execute("CREATE TEMPORARY TABLE _query_entities(gloss TEXT);")
    psycopg2.extras.execute_values(cur, "INSERT INTO _query_entities(gloss) VALUES %s", [(entity,) for entity, _ in entities])
    cur.execute("CREATE TEMPORARY TABLE _query_docs(doc_id TEXT);")
    psycopg2.extras.execute_values(cur, "INSERT INTO _query_docs(doc_id) VALUES %s", docs)

    cur.execute("""
SELECT q.gloss, COUNT(DISTINCT m.doc_id)
FROM mention m, _query_entities q, _query_docs d
WHERE m.gloss = q.gloss
  AND m.doc_id = d.doc_id
GROUP BY q.gloss
""")
    counts = {entity: count for entity, count in cur.fetchall()}
    conn.commit()
    cur.close()
    conn.close()

    return counts

def do_stats(args):
    obj = {}
    # Load list of entity counts
    mention_counts = load_counts(args.counts_mentions)
    # Load list of entity doc_counts
    doc_counts = load_counts(args.counts_docs)
    queries = [(e, 0) for e in mention_counts.keys()]
    keys = ["entropy", "mention_counts", "doc_counts", "doc_links"]

    for key, stat in zip(keys, compute_stats(queries, mention_counts, doc_counts)):
        key = "baseline_"+key
        obj[key] = stat

    if args.mode == "query":
        queries = [(line.strip(), 0) for line in args.queries]
        stats = [compute_stats(queries, mention_counts, doc_counts)]
    elif args.mode == "baseline":
        stats = []
        for i in range(10):
            docs = sample_docs_baseline(args.corpus, args.num_docs, args.sentence_table)
            queries = list((normalize_entity(entity), int(count)) for entity, count in query_entities(sorted(docs), mention_table=args.mention_table))
            stats_ = compute_stats(queries, mention_counts, doc_counts)
            stats.append()
            logger.info("stats: %s", stats[-1][:2])
    elif args.mode == "entity":
        stats = []
        for i in range(10):
            docs = sample_docs_entity(args.corpus, args.num_docs, args.per_entity, args.sentence_table, args.mention_table)
            queries = list((normalize_entity(entity), int(count)) for entity, count in query_entities(sorted(docs), mention_table=args.mention_table))
            stats.append(compute_stats(queries, mention_counts, doc_counts))
            logger.info("stats: %s", stats[-1][:2])
    else:
        raise NotImplementedError()

    # Combine the outputs.
    obj["query_entropy"] = np.mean([stat[0] for stat in stats]).tolist()
    obj["query_mention_counts"] = np.mean([stat[1] for stat in stats], axis=0).tolist()
    obj["query_mention_links"] = np.vstack(np.array(stat[2]) for stat in stats).tolist()
    obj["query_doc_counts"] = np.mean([stat[3] for stat in stats], axis=0).tolist()
    obj["query_doc_links"] = np.vstack(np.array(stat[4]) for stat in stats).tolist()

    for key, stat in obj.items():
        if "links" not in key:
            logger.info("%s=%s", key, stat)
    json.dump(obj, args.output)


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

    command_parser = subparsers.add_parser('stats', help='Plot statistics from sampling scheme for entities')
    command_parser.add_argument('-m', '--mode', choices=["query", "baseline", "entity"], default="query", help="Which sampling scheme?")
    command_parser.add_argument('-c', '--corpus', type=str, default="2015", help="Corpus to select documents from.")
    command_parser.add_argument('-n', '--num-docs', type=int, default=200, help="Number of documents to exhaustively sample")
    command_parser.add_argument('-p', '--per-entity', type=int, default=4, help="Number of documents to sample per entity")
    command_parser.add_argument('-mt', '--mention-table', type=str, default="mention", help="Mention table to use")
    command_parser.add_argument('-st', '--sentence-table', type=str, default="sentence", help="Sentence table")
    command_parser.add_argument('-iq', '--queries', type=argparse.FileType('r'), default="data/query_entities_2015.tsv", help="Path to counts of entity mentions")
    command_parser.add_argument('-cm', '--counts-mentions', type=argparse.FileType('r'), default="data/entity_counts.tsv", help="Path to counts of entity mentions")
    command_parser.add_argument('-cd', '--counts-docs', type=argparse.FileType('r'), default="data/entity_doc_counts.tsv", help="Path to counts of entity doc mentions")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default="entity_stats.json", help="A path to a folder to save documents.")
    command_parser.set_defaults(func=do_stats)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
