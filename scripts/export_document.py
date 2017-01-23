#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exports a document.
"""

import json
import sys
import shlex
import subprocess
from collections import namedtuple

from util import parse_psql_array

def query_psql(sql):
    """
    Sends a query to psql.
    """
    cmd = r"""psql -h localhost -p 4242 kbp kbp -c "COPY ({sql}) TO STDOUT DELIMITER E'\t'" """.format(sql=sql)
    output = subprocess.check_output(shlex.split(cmd))

    for line in output.split("\n"):
        line = line.strip()
        if len(line) == 0: continue
        yield line.split("\t")

def query_doc(docid):
    doc, idx_ = [], 0
    for row in query_psql("SELECT sentence_index, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end FROM sentence WHERE doc_id = '{}' ORDER BY sentence_index".format(docid)):
        idx, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = row
        assert int(idx) == idx_, "Seems to have skipped a line: {} != {}".format(idx, idx_)
        idx_ += 1
        words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = map(parse_psql_array, (words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end))
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

def do_command(args):
    doc = query_doc(args.docid)
    mentions = query_mentions(args.docid)
    args.output.write(json.dumps({
        "doc_id": args.docid,
        "sentences": doc,
        "mentions": mentions
        }))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Saves document to file in json format.')
    parser.add_argument('-d', '--docid', type=str, default="", help="DOCID")
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
