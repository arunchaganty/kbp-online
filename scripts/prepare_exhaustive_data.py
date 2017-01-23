#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare data for exhaustive evaluation.
"""

import os
import json
import sys
import shlex
import subprocess
import logging
from collections import defaultdict

from util import parse_psql_array, ensure_dir

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def query_psql(sql):
    """
    Sends a query to psql.
    """
    cmd = r"""psql -h localhost -p 4242 kbp kbp -c "COPY ({sql}) TO STDOUT DELIMITER E'\t'" """.format(sql=sql)
    output = subprocess.check_output(shlex.split(cmd)).decode("utf-8")

    for line in output.split("\n"):
        if len(line) == 0: continue
        yield line.split("\t")

def query_doc(docid):
    doc = []
    T = {
        "-LRB-": "(",
        "-RRB-": ")",
        "-LSB-": "[",
        "-RSB-": "]",
        "-LCB-": "{",
        "-RCB-": "}",
        "``": "\"",
        "''": "\"",
        "`": "'",
        }
    for row in query_psql("SELECT sentence_index, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end FROM sentence WHERE doc_id = '{}' ORDER BY sentence_index".format(docid)):
        idx, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = row

        # Happens in some DF
        #assert int(idx) == idx_, "Seems to have skipped a line: {} != {}".format(idx, idx_)
        words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = map(parse_psql_array, (words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end))
        words = list(map(lambda w: T.get(w, w), words))
        doc_char_begin, doc_char_end = map(int, doc_char_begin), map(int, doc_char_end)
        keys = ("word", "lemma", "pos_tag", "ner_tag", "doc_char_begin", "doc_char_end")
        tokens = [{k:v for k, v in zip(keys, values)} for values in zip(words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end)]
        doc.append(tokens)
    return doc

def query_mentions(docid):
    ner_map = {
        "PERSON": "PER",
        "ORGANIZATION": "ORG",
        "LOCATION": "GPE",
        "GPE": "GPE",
        "DATE": "DATE",
        "TITLE": "TITLE",
        }

    mentions = []
    for row in query_psql("""SELECT m.gloss, m.ner, m.doc_char_begin, m.doc_char_end, n.gloss AS canonical_gloss, m.best_entity, m.doc_canonical_char_begin, m.doc_canonical_char_end
    FROM mention m, mention n 
    WHERE m.doc_id = '{doc_id}' AND n.doc_id = m.doc_id 
      AND m.doc_canonical_char_begin = n.doc_char_begin AND m.doc_canonical_char_end = n.doc_char_end 
    ORDER BY m.doc_char_begin""".format(doc_id=docid)):
        gloss, ner, doc_char_begin, doc_char_end, entity_gloss, entity_link, entity_doc_char_begin, entity_doc_char_end = row
        if ner not in ner_map: continue
        ner = ner_map[ner]

        mentions.append({
            "gloss": gloss,
            "type": ner,
            "doc_char_begin": int(doc_char_begin),
            "doc_char_end": int(doc_char_end),
            "entity": {
                "gloss": entity_gloss,
                "link": entity_link,
                "doc_char_begin": int(entity_doc_char_begin),
                "doc_char_end": int(entity_doc_char_end),
                }
            })
    return mentions

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

def do_command(args):

    date_map = make_date_map(args.dates)
    # Create output folder.
    ensure_dir(args.output)
    for doc in collect_data(args.input, date_map):
        with open(os.path.join(args.output, doc['doc_id'] + ".json"), 'w') as f:
            json.dump(doc, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Saves document to file in json format.')
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default="data/english_edl.tab", help="Path to LDC2015E103 data")
    parser.add_argument('-d', '--dates', type=argparse.FileType('r'), default="data/english_edl.dates", help="Path to LDC2015E103 dates")
    parser.add_argument('-o', '--output', type=str, default="data/exhaustive/", help="A path to a folder to save documents.")
    parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
