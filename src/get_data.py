#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exports data from database.
"""

import json
import sys

from kbpo.db import query_doc, query_mentions

def do_doc(args):
    doc = query_doc(args.docid)
    mentions = query_mentions(args.docid)
    args.output.write(json.dumps({
        "doc_id": args.docid,
        "sentences": doc,
        "suggested-mentions": mentions
        }))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Exports different types of data from database into a json format.')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('doc', help='Get a document by doc-id')
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    command_parser.add_argument('docid', type=str, required=True, help="DOCID")
    command_parser.set_defaults(func=do_doc)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
