#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

import os
import json
import sys
import logging
from util import ensure_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def do_command(args):
    ensure_dir(args.output)
    for fname in os.listdir(args.input):
        if fname.endswith(".json"):
            with open(os.path.join(args.input, fname)) as f:
                doc = json.load(f)
            relations = doc['relations']
            for relation in relations:
                doc['relations'] = [relation]
                b1, e1 = relation['subject']['doc_char_begin'], relation['subject']['doc_char_end']
                b2, e2 = relation['object']['doc_char_begin'], relation['object']['doc_char_end']

                logger.info("Saving %s with %d relations", doc['doc_id'], len(doc['relations']))
                with open(os.path.join(args.output, "{}-{}-{}-{}-{}.json".format(doc['doc_id'], b1, e1, b2, e2)), 'w') as f:
                    json.dump(doc, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--input', type=str, default="data/pooled-eval", help="Input documents")
    parser.add_argument('-o', '--output', type=str, default="data/pooled-eval-flat", help="A path to a folder to save output.")
    parser.set_defaults(func=do_command)

    #subparsers = parser.add_subparsers()
    #command_parser = subparsers.add_parser('command', help='' )
    #command_parser.set_defaults(func=do_command)

    ARGS = parser.parse_args()
    ARGS.func(ARGS)
