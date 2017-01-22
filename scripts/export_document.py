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

def query_doc(docid):
    cmd = r"""psql -h localhost -p 4242 kbp kbp -c "COPY (SELECT sentence_index, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end FROM sentence WHERE doc_id = '{}' ORDER BY sentence_index) TO STDOUT DELIMITER E'\t'" """.format(docid)
    output = subprocess.check_output(shlex.split(cmd))

    doc = []
    idx_ = 0
    for line in output.split("\n"):
        line = line.strip()
        if len(line) == 0: continue 
        idx, words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = line.split("\t")

        assert int(idx) == idx_, "Seems to have skipped a line: {} != {}".format(idx, idx_)
        idx_ += 1

        words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end = map(parse_psql_array, (words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end))
        keys = ("word", "lemma", "pos_tag", "ner_tag", "doc_char_begin", "doc_char_end")
        tokens = [{k:v for k, v in zip(keys, values)} for values in zip(words, lemmas, pos_tags, ner_tags, doc_char_begin, doc_char_end)]
        doc.append(tokens)
    return doc

def do_command(args):
    doc = query_doc(args.docid)
    args.output.write(json.dumps(doc))

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
