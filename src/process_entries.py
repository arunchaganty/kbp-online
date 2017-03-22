#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performs sanity checks on mentions data.
"""

import csv
import sys
import logging

from kbpo.entry import parse_input, verify_mention_ids, verify_canonical_mentions, verify_relations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def do_validate(args):
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
    parser = argparse.ArgumentParser(description='Process and transform entry files')

    subparsers = parser.add_subparsers()
    command_parser = subparsers.add_parser('validate', help='Performs sanity checks and corrects simple mistakes')
    command_parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=sys.stdin, help="")
    command_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help="")
    command_parser.set_defaults(func=do_validate)

    ARGS = parser.parse_args()
    if ARGS.func is None:
        parser.print_help()
        sys.exit(1)
    else:
        ARGS.func(ARGS)
